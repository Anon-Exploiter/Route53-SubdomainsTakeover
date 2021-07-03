from utils.colors import *


def write(var, color, data):
    '''
    Printing data but with colors and [#]
    '''

    if var == None:
        print(f"{color}{str(data)}")

    elif var != None:
        print(f"{w}[{g}{var}{w}] {color} {str(data)}")


def heading(heading, color, afterWebHead):
    '''
    To print headings -- without having to write too much
    code for each

    ------------------------------
            Going to do XYZ
    ------------------------------
    '''
    space 	= " " * 15

    var     = f"{space}{heading}{afterWebHead} ...{space}"
    length 	= len(var) + 1
    
    print()
    print(f"{w}{'-' * length}")
    print(f"{color}{var}")
    print(f"{w}{'-' * length}")
    print()