from pymmcore import CMMCore

core = CMMCore()


if __name__ == "__main__":
    while True:
        i = input("go: ")
        if i == "quit":
            break
        print(eval(i))
