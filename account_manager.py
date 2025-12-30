"""
KZBIT Automation - Account Manager Module

Handles account loading, validation, and parallel execution.
Uses controlled batching to maximize throughput.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Optional

from config import ACCOUNTS_FILE, MAX_CONCURRENT_ACCOUNTS
from models import Account, AccountResult, CodeCommand, WorkflowResult
from browser import get_browser_manager
from automation import process_account
from timing import reset_global_deadline, get_global_deadline


class AccountManager:
    """
    Manages multiple accounts with parallel execution.
    
    Features:
    - Load and validate accounts from JSON
    - Controlled parallel execution (2-3 concurrent)
    - Dynamic queue management
    - Slow account detection
    """
    
    def __init__(self, accounts_file: Path = ACCOUNTS_FILE):
        self.accounts_file = accounts_file
        self.accounts: List[Account] = []
    
    def load_accounts(self) -> int:
        """
        Load accounts from JSON file.
        
        Returns:
            Number of accounts loaded
            
        Raises:
            FileNotFoundError: If accounts file doesn't exist
            ValueError: If validation fails
        """
        if not self.accounts_file.exists():
            return 0
        
        with open(self.accounts_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return 0
        
        if not isinstance(data, list):
            raise ValueError("Accounts file must contain a JSON array")
        
        self.accounts = []
        for i, item in enumerate(data):
            try:
                account = Account(**item)
                self.accounts.append(account)
            except Exception as e:
                print(f"Warning: Invalid account at index {i}: {e}")
        
        return len(self.accounts)

    def save_accounts(self) -> None:
        """Save current accounts to JSON file."""
        data = [acc.model_dump() for acc in self.accounts]
        with open(self.accounts_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def add_account(self, email: str, password: str) -> bool:
        """
        Add a new account if it doesn't already exist.
        
        Returns:
            True if added, False if already exists
        """
        self.load_accounts() # Ensure we have latest
        
        if any(acc.email == email for acc in self.accounts):
            return False
            
        self.accounts.append(Account(email=email, password=password))
        self.save_accounts()
        return True
    
    async def process_all(
        self,
        command: CodeCommand,
        on_result: Optional[callable] = None,
        max_concurrent: int = MAX_CONCURRENT_ACCOUNTS
    ) -> WorkflowResult:
        """
        Process all accounts with controlled parallelism.
        
        Uses a semaphore to limit concurrent contexts.
        Reports results in real-time via callback.
        
        Args:
            command: The code command (clicks + code)
            on_result: Optional callback for each account result
            max_concurrent: Maximum concurrent accounts
            
        Returns:
            WorkflowResult with all account results
        """
        # Reset global deadline
        reset_global_deadline()
        deadline = get_global_deadline()
        
        # Get browser manager
        browser = get_browser_manager()
        await browser.start()
        
        # Semaphore for controlled parallelism
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Results collection
        results: List[AccountResult] = []
        timed_out = False
        
        async def process_with_semaphore(account: Account) -> Optional[AccountResult]:
            """Process single account with semaphore control."""
            nonlocal timed_out
            
            # Check deadline before acquiring semaphore
            if deadline.is_expired:
                timed_out = True
                return None
            
            async with semaphore:
                # Double-check deadline after acquiring
                if deadline.is_expired:
                    timed_out = True
                    return None
                
                try:
                    async with browser.new_page() as page:
                        result = await process_account(
                            page,
                            account,
                            command.code,
                            command.clicks
                        )
                        
                        # Report result via callback
                        if on_result:
                            await self._call_callback(on_result, result)
                        
                        return result
                        
                except TimeoutError:
                    timed_out = True
                    return AccountResult(
                        email=account.email,
                        success=False,
                        total_submits=0,
                        successful_submits=0,
                        failed_submits=0,
                        duration_seconds=0,
                        error="Global deadline exceeded"
                    )
                except Exception as e:
                    return AccountResult(
                        email=account.email,
                        success=False,
                        total_submits=0,
                        successful_submits=0,
                        failed_submits=0,
                        duration_seconds=0,
                        error=str(e)
                    )
        
        # Create tasks for all accounts
        tasks = [
            asyncio.create_task(process_with_semaphore(account))
            for account in self.accounts
        ]
        
        # Wait for all to complete (or timeout)
        try:
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item in completed:
                if isinstance(item, AccountResult):
                    results.append(item)
                elif isinstance(item, Exception):
                    print(f"Task exception: {item}")
                    
        except Exception as e:
            print(f"Gather exception: {e}")
        
        # Build final result
        successful = sum(1 for r in results if r.success)
        
        return WorkflowResult(
            total_accounts=len(self.accounts),
            processed_accounts=len(results),
            successful_accounts=successful,
            total_duration_seconds=deadline.elapsed_seconds,
            timed_out=timed_out,
            account_results=results
        )
    
    async def _call_callback(self, callback, result: AccountResult) -> None:
        """Safely call callback (sync or async)."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(result)
            else:
                callback(result)
        except Exception as e:
            print(f"Callback error: {e}")


async def run_workflow(
    command: CodeCommand,
    accounts_file: Path = ACCOUNTS_FILE,
    on_result: Optional[callable] = None
) -> WorkflowResult:
    """
    Convenience function to run the complete workflow.
    
    Args:
        command: Parsed /code command
        accounts_file: Path to accounts JSON
        on_result: Optional callback for each result
        
    Returns:
        WorkflowResult with complete metrics
    """
    manager = AccountManager(accounts_file)
    
    try:
        count = manager.load_accounts()
        print(f"Loaded {count} accounts")
        
        if count == 0:
            return WorkflowResult(
                total_accounts=0,
                processed_accounts=0,
                successful_accounts=0,
                total_duration_seconds=0,
                timed_out=False,
                account_results=[]
            )
        
        return await manager.process_all(command, on_result)
        
    except Exception as e:
        print(f"Workflow error: {e}")
        return WorkflowResult(
            total_accounts=0,
            processed_accounts=0,
            successful_accounts=0,
            total_duration_seconds=0,
            timed_out=False,
            account_results=[]
        )
