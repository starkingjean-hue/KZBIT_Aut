"""
KZBIT Automation - Telegram Bot Module

Handles Telegram communication via python-telegram-bot.
Parses commands, launches workflows, reports results.
"""

import asyncio
import logging
import sys
import signal
from typing import Optional

from telegram import Update, constants
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
    Application,
)

from config import TELEGRAM_BOT_TOKEN
from models import CodeCommand, AccountResult, WorkflowResult
from account_manager import run_workflow
from browser import cleanup_browser
from timing import reset_global_deadline

# States for ConversationHandler
(
    AWAIT_ADMIN_ADD,
    AWAIT_DATA_ADD,
    AWAIT_ADMIN_SHOW
) = range(3)

ADMIN_CODE = "Jean@2010"

class TelegramBot:
    """
    Telegram bot for receiving commands and reporting results.
    
    Commands:
    - /code <CLICKS>f <CODE> : Submit code N times on all accounts
    - /status : Check bot status
    - /help : Show available commands
    - /add_c : Interactive account addition
    - /show : Interactive account listing
    """
    
    def __init__(self):
        self.application: Optional[Application] = None
        self._current_workflow: Optional[asyncio.Task] = None
    
    async def start(self) -> Application:
        """Initialize and start the Telegram application."""
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured in .env")
        
        self.application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Conversation for /add_c
        add_conv = ConversationHandler(
            entry_points=[CommandHandler("add_c", self._start_add_c)],
            states={
                AWAIT_ADMIN_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._check_admin_add)],
                AWAIT_DATA_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._process_data_add)],
            },
            fallbacks=[CommandHandler("cancel", self._cancel_conv)],
        )
        
        # Conversation for /show
        show_conv = ConversationHandler(
            entry_points=[CommandHandler("show", self._start_show)],
            states={
                AWAIT_ADMIN_SHOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, self._check_admin_show)],
            },
            fallbacks=[CommandHandler("cancel", self._cancel_conv)],
        )
        
        # Add handlers
        self.application.add_handler(CommandHandler("code", self._handle_code))
        self.application.add_handler(CommandHandler("status", self._handle_status))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("start", self._handle_help))
        self.application.add_handler(add_conv)
        self.application.add_handler(show_conv)
        
        # Manual start to have full control over signal/loop
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        print("Telegram bot started (Explicit Async Mode).")
        return self.application
    
    async def stop(self) -> None:
        """Stop the bot and cleanup."""
        if self._current_workflow and not self._current_workflow.done():
            self._current_workflow.cancel()
        
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        
        await cleanup_browser()

    async def run_forever(self) -> None:
        """Keep the bot running."""
        while True:
            await asyncio.sleep(1)

    async def _handle_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /code <CLICKS>f <CODE> command."""
        reset_global_deadline()
        if not update.message: return
        
        user = update.effective_user
        username = user.username or str(user.id)
        
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                "❌ **Format invalide**\n\n"
                "Le format requis est : `/code <NOMBRE>f <CODE>`\n"
                "Exemple : `/code 2f zhflehuih`",
                parse_mode=constants.ParseMode.MARKDOWN
            )
            return
        
        clicks_arg = args[0].lower()
        code = args[1]
        
        if not clicks_arg.endswith('f'):
            await update.message.reply_text("❌ Le nombre doit être suivi de **'f'** (ex: `2f`).")
            return
            
        try:
            clicks = int(clicks_arg[:-1])
            command = CodeCommand(clicks=clicks, code=code)
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur : {e}")
            return

        if self._current_workflow and not self._current_workflow.done():
            await update.message.reply_text("⏳ Workflow en cours...")
            return
        
        await update.message.reply_text(
            f"🚀 **Démarrage du workflow**\n\n"
            f"• Code : `{command.code}`\n"
            f"• Clics : `{command.clicks}f`\n"
            f"• Utilisateur : @{username}\n\n"
            f"🕒 Le système va traiter tous les comptes enregistrés par lots (3 max en simultané).",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        
        self._current_workflow = asyncio.create_task(self._run_workflow_task(update, command))

    # --- Conversation Callbacks ---
    
    async def _cancel_conv(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel current conversation."""
        await update.message.reply_text("❌ Action annulée.")
        return ConversationHandler.END

    # ADD_C Flow
    async def _start_add_c(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("🔑 Veuillez entrer le **Code Administrateur** pour ajouter un compte :")
        return AWAIT_ADMIN_ADD

    async def _check_admin_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.message.text == ADMIN_CODE:
            await update.message.reply_text(
                "✅ Code correct.\n\n"
                "Veuillez entrer les informations du compte au format suivant :\n"
                "`e:email@test.com m:password`",
                parse_mode=constants.ParseMode.MARKDOWN
            )
            return AWAIT_DATA_ADD
        else:
            await update.message.reply_text("⛔ Code incorrect. Conversation terminée.")
            return ConversationHandler.END

    async def _process_data_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text
        # Parsing basic e: m: format
        try:
            email = None
            password = None
            parts = text.split()
            for p in parts:
                if p.startswith("e:"): email = p[2:]
                if p.startswith("m:"): password = p[2:]
            
            if not email or not password:
                raise ValueError("Format e: ou m: manquant")
            
            from account_manager import AccountManager
            manager = AccountManager()
            if manager.add_account(email, password):
                await update.message.reply_text(f"✅ Compte `{email}` ajouté avec succès !")
            else:
                await update.message.reply_text(f"⚠️ Le compte `{email}` existe déjà.")
                
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur de format. Utilisez `e:email m:password`.\n(Erreur: {e})")
            return AWAIT_DATA_ADD
            
        return ConversationHandler.END

    # SHOW Flow
    async def _start_show(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("🔑 Veuillez entrer le **Code Administrateur** pour afficher les comptes :")
        return AWAIT_ADMIN_SHOW

    async def _check_admin_show(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if update.message.text == ADMIN_CODE:
            from account_manager import AccountManager
            manager = AccountManager()
            manager.load_accounts()
            
            if not manager.accounts:
                await update.message.reply_text("📭 Aucun compte enregistré.")
            else:
                msg = "👥 **Liste des Comptes ({})** :\n\n".format(len(manager.accounts))
                for i, acc in enumerate(manager.accounts, 1):
                    msg += f"{i}. `{acc.email}`\n"
                await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⛔ Code incorrect.")
            
        return ConversationHandler.END

    # --- Existing logic ---

    async def _run_workflow_task(self, update: Update, command: CodeCommand) -> None:
        """Task to execute workflow and report results."""
        
        async def on_account_result(result: AccountResult) -> None:
            """Report each account result with grouping logic."""
            def format_group(results_list, is_success: bool) -> str:
                if not results_list: return ""
                counts = {}
                for r in results_list:
                    msg = r.popup_text if r.popup_text else "Pas de message"
                    counts[msg] = counts.get(msg, 0) + 1
                
                total = len(results_list)
                emoji = "✅" if is_success else "❌"
                label = "gagné" if is_success else "échoué"
                if total > 1: label += "s"
                
                if len(counts) == 1:
                    msg = list(counts.keys())[0]
                    return f"{emoji} {total} {label}: {msg}"
                else:
                    details = ", ".join([f"{count} disent \"{msg}\"" for msg, count in counts.items()])
                    return f"{emoji} {total} {label} ({details})"

            success_list = [r for r in result.results if r.success]
            fail_list = [r for r in result.results if not r.success]
            
            summary_lines = []
            if fail_list:
                summary_lines.append(format_group(fail_list, False))
            if success_list:
                summary_lines.append(format_group(success_list, True))
            
            popup_summary = "\n".join(summary_lines) if summary_lines else "🔔 Aucun résultat."

            # Header Emoji
            if result.success:
                header_emoji = "✅"
            elif result.successful_submits > 0:
                header_emoji = "⚠️"
            else:
                header_emoji = "❌"
            
            message = (
                f"{header_emoji} **{result.email}**\n"
                f"• Statut : {'SUCCÈS' if result.success else 'PARTIEL' if result.successful_submits > 0 else 'ÉCHEC'}\n"
                f"• Temps : {result.duration_seconds:.1f}s\n"
                f"{popup_summary}"
            )
            
            if result.error:
                message += f"\n• ❗ Erreur fatale : {result.error}"
            
            await update.message.reply_text(message, parse_mode=constants.ParseMode.MARKDOWN)

        try:
            from account_manager import run_workflow
            result = await run_workflow(command, on_result=on_account_result)
            
            total = len(result.account_results)
            full_success = sum(1 for r in result.account_results if r.success)
            partial = sum(1 for r in result.account_results if not r.success and r.successful_submits > 0)
            failed = total - full_success - partial
            
            summary = (
                f"📊 **RÉSULTAT FINAL DU WORKFLOW**\n\n"
                f"• Comptes totaux : {total}\n"
                f"• ✅ Succès Complets : {full_success}\n"
                f"• ⚠️ Succès Partiels : {partial}\n"
                f"• ❌ Échecs : {failed}\n"
                f"• Durée : {result.total_duration_seconds:.1f}s"
            )
            
            if result.timed_out:
                summary += "\n⚠️ **TIMEOUT** (10m dépassés)"
            
            await update.message.reply_text(summary, parse_mode=constants.ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ **Erreur critique** : {e}")

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        status = "🟢 En attente"
        if self._current_workflow and not self._current_workflow.done():
            status = "🟡 Workflow en cours"
        await update.message.reply_text(f"🤖 **Statut** : {status}", parse_mode=constants.ParseMode.MARKDOWN)

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help and /start command."""
        await update.message.reply_text(
            "🤖 **Bot KZBIT Automation - Guide**\n\n"
            "Ce bot automatise la soumission de codes BTC.\n\n"
            "🚀 **Commandes :**\n"
            "• `/code <N>f <code>` : Lance le workflow.\n"
            "• `/status` : État du bot.\n"
            "• `/help` : Ce guide.\n\n"
            "🔐 **Administration :**\n"
            "• `/add_c` : Ajouter un compte (Demande le code verification).\n"
            "• `/show` : Liste les comptes (Demande le code verification).\n\n"
            "💡 **Note sur les comptes :**\n"
            "Le système traite tous les comptes dans `accounts.json` de manière optimisée. "
            "Si vous avez 5 comptes, ils seront traités par vagues pour respecter les délais.",
            parse_mode=constants.ParseMode.MARKDOWN
        )

async def start_bot() -> TelegramBot:
    """Create and start the Telegram bot."""
    bot = TelegramBot()
    await bot.start()
    return bot
