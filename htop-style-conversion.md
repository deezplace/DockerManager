# htop-style CLI conversion

A reusable prompt for converting a menu-driven, linefeeding Python CLI (prints a
menu, reads a choice, prints more lines below, repeat) into a persistent,
static-screen display like `htop`/`top`: the screen redraws in place instead of
scrolling, and the process stays running until the user explicitly quits.

Reference implementation: `dockman.py` in this repo.

## Prompt

Paste this into Claude Code (or similar) inside the target project, adjusting
the bracketed bits:

> Convert `[script.py]` to behave like an htop-style persistent CLI instead of
> a linefeeding menu:
>
> 1. **Static full-screen redraw.** On every loop iteration, clear the screen
>    with `\033[2J\033[H` (write + flush to stdout) before printing anything,
>    so the display redraws in place rather than scrolling. Add a bold title
>    bar centered to the terminal width (`shutil.get_terminal_size()`) with a
>    `-` separator line beneath it, then the status list, then the menu.
> 2. **Status list coloring.** Whatever the tool lists (containers, services,
>    jobs, hosts, …), color-code each entry by state: green for the healthy /
>    good state, yellow for unhealthy / warning state, default color for
>    anything without a defined state. Show the state as a bracketed tag, e.g.
>    `[healthy]` / `[unhealthy]`, in the matching color.
> 3. **Stay running.** Remove any `break`/exit that happens after performing
>    an action (start/stop/apply/whatever). After an action runs, print its
>    output normally (screen isn't cleared mid-action), then block on
>    `input("Press Enter to continue...")` so the output is readable, then
>    loop back to the static redraw. The process should only end via the
>    explicit quit menu option or Ctrl-C.
> 4. **Clean Ctrl-C.** Wrap the top-level call to the main loop in
>    `try/except KeyboardInterrupt`, print a short message like
>    `user chose to exit`, and call `sys.exit(0)` — no traceback, exit code 0.
>    The existing quit menu option should already exit 0 normally; leave it
>    as-is unless it doesn't.
> 5. **Don't exit on stray Enter.** If pressing Enter with no input used to
>    quit the program, change that to a refresh instead — an accidental
>    blank Enter shouldn't kill a persistent display.
>
> Keep everything else about the tool's behavior and menu structure the same;
> this is a display/lifecycle change, not a feature change.

## What changed in `dockman.py` (concrete example)

- Added `clear_screen()` (`\033[2J\033[H`) and `print_header()` (bold,
  width-centered title + separator), called at the top of every loop
  iteration.
- Added `is_healthy()` alongside the existing `is_unhealthy()`; container
  names/tags are now green `[healthy]`, yellow `[unhealthy]`, or uncolored if
  no healthcheck is defined.
- Removed the `break` after `start`/`stop`/`down` actions; added
  `input("  Press Enter to continue...")` after running an action so output
  is visible before the next redraw.
- Wrapped `main()` in the `__main__` block with
  `try/except KeyboardInterrupt: print("\n  user chose to exit"); sys.exit(0)`.
- Blank input at the main menu now falls into the refresh branch instead of
  the exit branch.
