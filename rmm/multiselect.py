#!/usr/bin/env python3

import curses


class WindowSizeException(Exception):
    pass


class AbortModOrderException(Exception):
    pass


def multiselect_order_menu(stdscr, data):
    data = [(n.packageid, n.enabled) for n in data]
    k = 0

    # Clear and refresh the screen for a blank canvas
    stdscr.clear()
    stdscr.refresh()

    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

    selection = 0
    window_height, window_width = stdscr.getmaxyx()
    scroll_window_height = window_height - 10
    scroll_window_position = 0

    if window_width < 40 or window_height < 15:
        raise WindowSizeException()

    def check_bounds(location, data, delta_position):
        if delta_position > 0:
            if location < len(data) - 1:
                return True
        if delta_position < 0:
            if location > 0:
                return True
        return False

    def move_selection(selected, l, d):
        if d > 0 and check_bounds(selected, l, d):
            return selected + 1
        if d < 0:
            if selected > 0 and check_bounds(selected, l, d):
                return selected - 1
        return selected

    def list_swap(data, offset, pos):
        temp = data[offset], data[offset + pos]
        data[offset + pos] = temp[0]
        data[offset] = temp[1]

    while True:
        # Initialization
        stdscr.clear()
        window_height, window_width = stdscr.getmaxyx()

        if k == curses.KEY_DOWN:
            selection = move_selection(selection, data, 1)
        elif k == curses.KEY_UP:
            selection = move_selection(selection, data, -1)
        elif k == ord("j"):
            if check_bounds(selection, data, 1):
                list_swap(data, selection, 1)
                selection = move_selection(selection, data, 1)
        elif k == ord("k"):
            if check_bounds(selection, data, -1):
                list_swap(data, selection, -1)
                selection = move_selection(selection, data, -1)
        elif k == curses.KEY_ENTER or k == 10 or k == 13:
            data[selection] = (data[selection][0], not data[selection][1])
            selection = move_selection(selection, data, 1)

        elif k == ord("c"):
            return data

        elif k == ord("q"):
            raise AbortModOrderException()

        if scroll_window_position < len(data) - 1 and selection > (
            scroll_window_position + scroll_window_height - 1
        ):
            scroll_window_position += 1
        if scroll_window_position > 0 and selection < (scroll_window_position):
            scroll_window_position -= 1

        statusbarstr = "Press 'c' to accept changes, 'q' to exit without saving, 'Enter' to enable/disable, 'j/k' to change order."

        max_length = 0
        for n in data:
            if len(n[0]) > max_length:
                max_length = len(n[0])

        scroll_centering_value = (
            scroll_window_height if scroll_window_height < len(data) else len(data)
        )
        start_y = int(
            (window_height // 2)
            - int(scroll_centering_value) // 2
            - int(scroll_centering_value) % 2
        )
        start_x = int((window_width // 2) - int(max_length) // 2)

        for i, (k, v) in enumerate(
            data[scroll_window_position : scroll_window_position + scroll_window_height]
        ):
            if v == False:
                stdscr.addstr(start_y, start_x - 3, "-")
            if v == True:
                stdscr.addstr(start_y, start_x - 3, "+")
            if selection == i + scroll_window_position:
                stdscr.attron(curses.A_STANDOUT)
            stdscr.addstr(start_y, start_x, k)
            if selection == i + scroll_window_position:
                stdscr.attroff(curses.A_STANDOUT)
            start_y += 1

        # Rendering some text
        title = "RMM: Mod Sorting Display"
        stdscr.addstr(0, 0, title, curses.color_pair(1))

        # Render status bar
        stdscr.attron(curses.color_pair(3))
        stdscr.addstr(window_height - 1, 0, statusbarstr[0 : window_width - 1])
        if window_width > len(statusbarstr):
            stdscr.addstr(
                window_height - 1,
                len(statusbarstr),
                " " * (window_width - len(statusbarstr) - 1),
            )
        stdscr.attroff(curses.color_pair(3))

        # Refresh the screen
        stdscr.refresh()

        # Wait for next input
        k = stdscr.getch()


def main():
    text = [
        ("jaxe.rimhud", True),
        ("fluffies.desirepaths", False),
        ("i eat bagels", False),
        ("chonky.cats", False),
    ]
    print(curses.wrapper(multiselect_order_menu, text))


if __name__ == "__main__":
    main()
