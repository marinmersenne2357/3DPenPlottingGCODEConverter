import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.font import Font
from tkinter import StringVar
import re
# pyinstaller --onefile --windowed GCODE_GUI.py


def open_input_file():
    # prompt Windows file open dialog for input file
    input_file_path = filedialog.askopenfilename(
        title="Select your gcode input file",
        filetypes=[("GCODE files", "*.gcode*"), ("Text files", "*.txt"), ("All files", "*.*")]
    )
    if input_file_path:
        input_file_entry.delete(0, tk.END)
        input_file_entry.insert(0, input_file_path)


def open_output_file():
    # prompt Windows file open dialog for output file
    output_file_path = filedialog.asksaveasfilename(
        title="Select your output gcode file",
        filetypes=[("GCODE files", "*.gcode*"), ("Text files", "*.txt"), ("All files", "*.*")]
    )
    if output_file_path:
        output_file_entry.delete(0, tk.END)
        output_file_entry.insert(0, output_file_path)


def search_and_replace(content, search_string, replace_string):
    # substitutes all unique instances of a search string.
    pattern = r'\b' + re.escape(search_string) + r'\b'
    return re.sub(pattern, replace_string, content)


def add_to_lines(content, flag, code, value):
    # appends a string to lines which contain the specified flag,
    # (provided that a feed isn't already in the line)
    modified_lines = []
    for line in content:
        if flag in line and 'F' not in line:
            line = line.rstrip() + ' ' + code + value
        modified_lines.append(line)
    return modified_lines


def calculate_bounds(content, flag1, flag2):
    # Computes the maximum G1 cutting dimensions of the gcode part
    last_positive_x_value = 0
    last_positive_y_value = 0
    last_negative_x_value = 0
    last_negative_y_value = 0
    # for every line, check that the X/Y is there, and pull out the numerical value
    # only keep the largest value that is encountered
    for i, line in enumerate(content):
        if flag1 or flag2 in line:
            if 'X' in line:
                x_start_index = line.index('X') + 1
                x_end_index = line.index(' ', x_start_index)
                x_value = float(line[x_start_index:x_end_index])
                # if i == 1 or i == 2:
                #    debug_var.set(f'{x_value}')
                if x_value < 0:
                    if last_negative_x_value < abs(x_value):
                        last_negative_x_value = abs(x_value)
                elif x_value > 0:
                    if last_positive_x_value < x_value:
                        last_positive_x_value = x_value

            if 'Y' in line:
                y_start_index = line.index('Y') + 1

                try:
                    y_value = float(line[y_start_index:])
                except ValueError:
                    y_end_index = line.index(' ', y_start_index)
                    y_value = float(line[y_start_index:y_end_index])

                if y_value < 0:
                    if last_negative_y_value < abs(y_value):
                        last_negative_y_value = abs(y_value)
                elif y_value > 0:
                    if last_positive_y_value < y_value:
                        last_positive_y_value = y_value

    return [last_negative_x_value + last_positive_x_value, last_negative_y_value + last_positive_y_value]


def offset_cell(n_x, s_x, n_y, s_y, tiling_scale, content_cell):
    # Before each page cycle is repeated, we need to repeat the unit cell gcode n * m times,
    # offsetting the cell the requisite distances in x and y each time.
    # The absolute offsets should be added to each cell (the code remains in absolute coordinates).
    offset_tile_set_list = []
    # offset_content_single = ''
    # loop through each 'tile' (user inputted gcode), and for each tile,
    # loop through each line.
    for i in range(n_x):
        for j in range(n_y):
            offset_cell_content_list = []
            # debug_var.set(f'i: {i} j: {j}')
            # Calculate the offsets
            offset_x = i * s_x
            offset_y = j * s_y
            # For every line, check that the X/Y is there, and apply the requisite offsets to
            # the extracted absolute coordinates, finally putting it back into the gcode.
            # x_value = 0
            # y_value = 0
            for k, line in enumerate(content_cell):
                # debug_var.set(f'k: {k}')
                # if k == 1:
                #   debug_var.set(line)
                if 'G01' in line or 'G00' in line:
                    # debug_var.set(line)
                    if 'X' in line:
                        # debug_var.set(line)
                        x_start_index = line.index('X') + 1
                        x_end_index = line.find(' ', x_start_index)
                        if x_end_index == -1:
                            x_end_index = len(line)
                        modified_x_value = float(line[x_start_index:x_end_index]) * tiling_scale + offset_x
                        line = line[:x_start_index] + f'{modified_x_value}' + line[x_end_index:]

                        # debug_var.set(f'Offset line: {line}')
                        # debug_var.set(f'SF,EF: {line[:x_start_index]}~~{line[x_end_index:]}')
                        # debug_var.set(f'Offset line: {line}')

                    if 'Y' in line:
                        y_start_index = line.index('Y') + 1
                        y_end_index = line.find(' ', y_start_index)
                        if y_end_index == -1:
                            y_end_index = len(line)
                        modified_y_value = float(line[y_start_index:y_end_index]) * tiling_scale + offset_y
                        line = line[:y_start_index] + f'{modified_y_value}' + line[y_end_index:]

                # for every line, add the offset line to the cell content list
                offset_cell_content_list.append(line)
                # debug_var.set(f'Offset line list: {offset_cell_content_list}')
            # after all the lines added, convert cell to a string and add to the tile set list.
            offset_cell_content = '\n'.join(offset_cell_content_list) + '\n'
            # debug_var.set(f'Offset cell content: {offset_cell_content}')
            offset_tile_set_list.append(offset_cell_content)
    # Join the set of offset tiles back into a single string
    offset_tile_set = '\n'.join(offset_tile_set_list) + '\n'
    return offset_tile_set


def process_file():
    # get the file paths and preamble text from the GUI
    input_file_path = input_file_entry.get()
    output_file_path = output_file_entry.get()
    preamble = preamble_text.get("1.0", tk.END).strip()
    cycle_subroutine = cycles_text.get("1.0", tk.END).strip()
    # make sure that files have actually been selected
    if not input_file_path or not output_file_path:
        messagebox.showerror("Error", "Please select both input and output files.")
        return

    try:
        with open(input_file_path, 'r') as file:
            content = file.read()
        # Get search and replace strings from GUI
        # mso = M start old
        # meo = M end old
        # msn = M start new
        # men = M end new
        mso = mso_entry.get()
        meo = meo_entry.get()
        msn = msn_entry.get()
        men = men_entry.get()
        cut_feed = cut_feed_entry.get()
        trav_feed = trav_feed_entry.get()
        cycles = cycles_entry.get()
        cycle_offset = cycle_offset_entry.get()
        tiling_n_x = tiling_n_x_entry.get()
        tiling_n_y = tiling_n_y_entry.get()
        tiling_s_x = tiling_s_x_entry.get()
        tiling_s_y = tiling_s_y_entry.get()
        tiling_scale = tiling_scale_entry.get()

        # list of all user inputs which want to be integers
        numerical_input_name_list = ['Cutting Speed',
                                     'Travel Speed',
                                     'No. Cycles',
                                     'Cycle Offset',
                                     'No. Tiles X',
                                     'Tile Spacing X',
                                     'No. Tiles Y',
                                     'Tile Spacing Y',
                                     'Tile Scale']
        numerical_input_value_list = [cut_feed,
                                      trav_feed,
                                      cycles,
                                      cycle_offset,
                                      tiling_n_x,
                                      tiling_s_x,
                                      tiling_n_y,
                                      tiling_s_y,
                                      tiling_scale]

        # Convert numerical inputs to integers
        # loop through the numerical input lists and attempt to type cast to int.
        for i, numerical_input in enumerate(numerical_input_value_list):
            try:
                numerical_input = float(numerical_input)
            except ValueError:
                messagebox.showwarning(
                    "Invalid Input",
                    f"Invalid input for {numerical_input_name_list[i]}. Please enter an integer."
                )
                numerical_input_value_list[i] = 0  # Set default value to 0

        # update all the numerical variables with their integer cast values
        # (feeds are going back into strings so conversion unnecessary)
        cycles = int(numerical_input_value_list[2])
        cycle_offset = float(numerical_input_value_list[3])
        tiling_n_x = int(numerical_input_value_list[4])
        tiling_s_x = int(numerical_input_value_list[5])
        tiling_n_y = int(numerical_input_value_list[6])
        tiling_s_y = int(numerical_input_value_list[7])
        tiling_scale = float(numerical_input_value_list[8])

        # compute bounds of work area and update the GUI
        x_bound, y_bound = calculate_bounds(content.split('\n'), 'G01', 'G00')
        x_work_bound = x_bound * tiling_scale * tiling_n_x + (int(tiling_n_x) - 1) * tiling_s_x
        y_work_bound = y_bound * tiling_scale * tiling_n_y + (int(tiling_n_y) - 1) * tiling_s_y
        bounds_var.set('Part Bounds: X: ' + str(x_bound * tiling_scale) + 'mm  Y: ' + str(y_bound*tiling_scale) + 'mm\n' +
                       'Work Bounds: X: ' + str(x_work_bound) +
                       'mm  Y: ' + str(y_work_bound) + 'mm')

        # Repeat the tool paths for the requested number of cycles
        content_single = search_and_replace(content, 'M02', '')

        # Before each page cycle is repeated, we need to repeat the unit cell gcode n * m times,
        # offsetting the cell the requisite distances in x and y each time.
        # The absolute offsets should be added to each cell (the code remains in absolute coordinates).
        content_single = offset_cell(tiling_n_x, tiling_s_x, tiling_n_y, tiling_s_y, tiling_scale, content_single.split('\n'))

        content_loop = content_single
        # debug_var.set(f'Cycles: {cycles}')
        for i in range(cycles - 1):
            z_offset = i * cycle_offset
            content_loop = content_loop + f'\nG01 Z{z_offset}\nG92 Z0' + cycle_subroutine + content_single
        content = content_loop + '\n' + 'M02'

        # add skirt tool path to beginning of gcode, and a short safety dwell
        skirt_minor = (f'G01 X{x_bound * tiling_scale} Y0\n'
                 f'G01 X{x_bound * tiling_scale} Y{y_bound * tiling_scale}\n'
                 f'G01 X0 Y{y_bound * tiling_scale}\n'
                 f'G01 X0 Y0\n'
                 'G4 S2') + '\n'

        skirt_major = (f'G01 X{x_work_bound} Y0\n'
                 f'G01 X{x_work_bound} Y{y_work_bound}\n'
                 f'G01 X0 Y{y_work_bound}\n'
                 f'G01 X0 Y0\n'
                 'G4 S2') + '\n'


        # add preamble text to beginning of gcode
        new_content = preamble + '\n' + skirt_minor + skirt_major + '\n' + content

        # Find and replace the cut M commands from the gcode
        new_content = search_and_replace(new_content, mso, msn)
        new_content = search_and_replace(new_content, meo, men)

        # Add feeds after every G00 and G01 move command
        new_content = add_to_lines(new_content.split('\n'), 'G01', 'F', cut_feed)
        new_content = add_to_lines(new_content, 'G00', 'F', trav_feed)

        # Add a new-line character to each list item and join back into a single string
        new_list = [item + '\n' for item in new_content]
        new_content = ''.join(new_list)

        # Write to output file
        with open(output_file_path, 'w') as file:
            file.write(new_content)

        messagebox.showinfo("Success",
                            f"File processed and saved: {output_file_path}")
    # Please don't be used :/
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")


# Create main window
root = tk.Tk()
root.title("3D Printer Pen Plotting GCODE Processor")

# Input file selection
tk.Label(root, text="Input File:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
input_file_entry = tk.Entry(root, width=50)
input_file_entry.grid(row=0, column=1, padx=5, pady=5)
tk.Button(root, text="Browse", command=open_input_file).grid(row=0, column=2, padx=5, pady=5)
input_file_entry.insert(0, 'Select your input file (.txt, .gcode)')

# Output file selection
tk.Label(root, text="Output File:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
output_file_entry = tk.Entry(root, width=50)
output_file_entry.grid(row=1, column=1, padx=5, pady=5)
tk.Button(root, text="Browse", command=open_output_file).grid(row=1, column=2, padx=5, pady=5)
output_file_entry.insert(0, 'Select your output file (.txt, .gcode)')

# Command inputs
tk.Label(root, text="Existing start-cut GCODE:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
mso_entry = tk.Entry(root)
mso_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)
mso_entry.insert(0, "M09")

tk.Label(root, text="Existing end-cut GCODE:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
meo_entry = tk.Entry(root)
meo_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)
meo_entry.insert(0, "M10")

tk.Label(root, text="New start-cut GCODE:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
msn_entry = tk.Entry(root)
msn_entry.grid(row=4, column=1, sticky="w", padx=5, pady=5)
msn_entry.insert(0, "G01 Z-3")

tk.Label(root, text="New end-cut GCODE:").grid(row=5, column=0, sticky="e", padx=5, pady=5)
men_entry = tk.Entry(root)
men_entry.grid(row=5, column=1, sticky="w", padx=5, pady=5)
men_entry.insert(0, "G01 Z0")

tk.Label(root, text="Cutting speed (mm/min):").grid(row=6, column=0, sticky="e", padx=5, pady=5)
cut_feed_entry = tk.Entry(root)
cut_feed_entry.grid(row=6, column=1, sticky="w", padx=5, pady=5)
cut_feed_entry.insert(0, "4500")

tk.Label(root, text="Travel speed (mm/min):").grid(row=7, column=0, sticky="e", padx=5, pady=5)
trav_feed_entry = tk.Entry(root)
trav_feed_entry.grid(row=7, column=1, sticky="w", padx=5, pady=5)
trav_feed_entry.insert(0, "9000")

tk.Label(root, text="No. cycles:").grid(row=8, column=0, sticky="e", padx=5, pady=5)
cycles_entry = tk.Entry(root)
cycles_entry.grid(row=8, column=1, sticky="w", padx=5, pady=5)
cycles_entry.insert(0, "2")

tk.Label(root, text="Cycle z-offset (mm):").grid(row=9, column=0, sticky="e", padx=5, pady=5)
cycle_offset_entry = tk.Entry(root)
cycle_offset_entry.grid(row=9, column=1, sticky="w", padx=5, pady=5)
cycle_offset_entry.insert(0, "-0.086")

# Tiling
(tk.Label(root, text="No. tiles X:")
 .grid(row=10, column=0, sticky="e", padx=5, pady=5))
tiling_n_x_entry = tk.Entry(root)
tiling_n_x_entry.grid(row=10, column=1, sticky="w", padx=5, pady=5)
tiling_n_x_entry.insert(0, "1")

(tk.Label(root, text="Tile spacing X (mm):")
 .grid(row=11, column=0, sticky="e", padx=5, pady=5))
tiling_s_x_entry = tk.Entry(root)
tiling_s_x_entry.grid(row=11, column=1, sticky="w", padx=5, pady=5)
tiling_s_x_entry.insert(0, "10")

(tk.Label(root, text="No. tiles Y:")
 .grid(row=12, column=0, sticky="e", padx=5, pady=5))
tiling_n_y_entry = tk.Entry(root)
tiling_n_y_entry.grid(row=12, column=1, sticky="w", padx=5, pady=5)
tiling_n_y_entry.insert(0, "1")

(tk.Label(root, text="Tile spacing Y (mm):")
 .grid(row=13, column=0, sticky="e", padx=5, pady=5))
tiling_s_y_entry = tk.Entry(root)
tiling_s_y_entry.grid(row=13, column=1, sticky="w", padx=5, pady=5)
tiling_s_y_entry.insert(0, "10")

(tk.Label(root, text="Tile Scale")
 .grid(row=14, column=0, sticky="e", padx=5, pady=5))
tiling_scale_entry = tk.Entry(root)
tiling_scale_entry.grid(row=14, column=1, sticky="w", padx=5, pady=5)
tiling_scale_entry.insert(0, "1")

# Preamble text box
small_font = Font(family="Helvetica", size=8)  # Define a smaller font
tk.Label(root, text="GCODE Preamble:").grid(row=15, column=0, sticky="ne", padx=5, pady=5)
preamble_text = tk.Text(root, height=5, width=50, font=small_font, wrap=tk.NONE)
preamble_text.grid(row=15, column=1, columnspan=1, padx=10, pady=5)
preamble_text.insert(tk.END, """M201 X1000 Y1000 Z1000 E5000 ; sets maximum accelerations, mm/sec^2
M203 X400 Y400 Z48 E120 ; sets maximum feedrates, mm / sec
M204 S400 T1250 ; sets acceleration (S) and retract acceleration (R), mm/sec^2
M205 X8.00 Y8.00 Z0.40 E1.50 ; sets the jerk limits, mm/sec
M205 S0 T0 ; sets the minimum extruding and travel feed rate, mm/sec

;TYPE:Custom
; Initial setups
G90 ; use absolute coordinates
G92 ; reset coordinates to 0
G01 Z-3 F100
G01 Z0 F100
G4 S2
;
; """)

# Repeater text box
small_font = Font(family="Helvetica", size=8)  # Define a smaller font
tk.Label(root, text="Next-Cycle Subroutine GCODE:").grid(row=16, column=0, sticky="ne", padx=5, pady=5)
cycles_text = tk.Text(root, height=5, width=50, font=small_font, wrap=tk.NONE)
cycles_text.grid(row=16, column=1, columnspan=1, padx=10, pady=5)
cycles_text.insert(tk.END, """;;;;;;;;;;;;;;;;;;;;;;;
G01 Z0
G4 S2
G01 X100 Y-10
M106 S255
G01 Z-3 F500
G4 S3
G01 Z20 F250
G00 Y200 Z200 
M107
G00 X0 Y-10 Z0
G00 Z-3
G01 X100
G01 Z0
G00 X0 Y0
;;;;;;;;;;;;;;;;;;;;;;;;;;;\n
""")

# Description text box
tk.Label(root, text="Description:").grid(row=17, column=0, sticky="ne", padx=5, pady=5)
description_text = tk.Text(root, height=5, width=50, font=small_font, wrap=tk.WORD)
description_text.grid(row=17, column=1, columnspan=1, padx=10, pady=5)
description_text.insert(tk.END, "This program is designed to process basic 2D gcode from: "
                                "https://cnc-apps.com/en/app/dxf2gcode\n"
                                "The program will search and replace the default start and end-cut M-Commands with "
                                "user-specified ones suitable to their machine, as well as inserting both cut "
                                "and travel feed rates. For most machines, M106-M107 control the extruder fan, "
                                "providing a convenient 12/24V switchable power source. Z axis movements can also be "
                                "used. "
                                "GCODE from the user can also be tiled in the X and Y directions,"
                                "with specified spacings and numbers."
                                "The tile sets can be cycled a specified number of times, with provision for a "
                                "z offset for each cycle (e.g. plotting every page"
                                " of a book offsetting by page thickness). "
                                "A GCODE subroutine can be specified at the end of each cycle, "
                                "for example to flip the page of the book being plotted on"
                                " The online gcode converter"
                                " should be set to MARK, DXF arc as polyline: Yes, "
                                "Coordinates: Absolute, and M codes on.\n"
                                "See: https://reprap.org/wiki/G-code\n for a full list "
                                "of gcode commands.\n\n"
                                """
Example Input GCODE: \n
G21
M10
G00 X0 Y0
M09
G01 X125 Y0
G01 X125 Y75
G01 X0 Y75
G01 X0 Y0
M10
G00 X21.5 Y27.5
M09
G01 X21.4772 Y27.76047
G01 X21.4095 Y28.01303
G01 X21.299 Y28.25
G01 X21.1491 Y28.46418
G01 X20.9642 Y28.64907
G01 X20.75 Y28.79904
G01 X20.513 Y28.90954
G01 X20.2605 Y28.97721
M10
G00 X0 Y0
M02""")

# Display work area bounds
bounds_var = StringVar()
bounds_var.set('Work Bounds: Pending data input')
bounds_label = tk.Label(root, textvariable=bounds_var, font=small_font)
bounds_label.grid(row=18, column=0, columnspan=2, padx=10, pady=5)

# Debugging box
debug_var = StringVar()
debug_var.set('DEBUGGER OUTPUT')
debug_label = tk.Label(root, textvariable=debug_var, font=small_font)
debug_label.grid(row=19, column=0, columnspan=2, padx=10, pady=5)

# Process button
tk.Button(root, text="Process File", command=process_file).grid(row=20, column=0, pady=20)

root.mainloop()
