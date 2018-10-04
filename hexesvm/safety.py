def print_info():
    print("")
    print("####################################################")
    print("#  _    _     __   __       _______      ____  __  #")
    print("# | |  | |    \ \ / /      / ____\ \    / /  \/  | #")
    print("# | |__| | ___ \ V / ___  | (___  \ \  / /| \  / | #")
    print("# |  __  |/ _ \ > < / _ \  \___ \  \ \/ / | |\/| | #")
    print("# | |  | |  __// . \  __/  ____) |  \  /  | |  | | #")
    print("# |_|  |_|\___/_/ \_\___| |_____/    \/   |_|  |_| #")
    print("#                                                  #")
    print("####################################################")
    print("")
    
def aknowledge_risks():
    print("This script will automatically TURN ON HIGH VOLTAGES")
    print("This is a potentially dangerous operation!")
    print("Make sure that the cables are connected properly")
    print("and that the cryostat is closed!")
    print("")
    answer = input("Proceed [yes/no] ")
    if answer != "yes":
        exit()
    print("")
    