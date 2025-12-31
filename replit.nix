{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.playwright-driver.browsers
  ];
}
