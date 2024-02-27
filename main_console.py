# main_console.py
from multiprocessing import Process
from  user_input2 import collect_sell_buy_input, collect_buy_sell_input
from trading_record_manager import create_and_start_cycle_set_sell_buy, create_and_start_cycle_set_buy_sell

def start_cycleset_sell_buy(user_config):
    process_sell_buy = Process(target=create_and_start_cycle_set_sell_buy, args=(user_config,))
    process_sell_buy.name = 'cycleset_sell_buy'
    process_sell_buy.start()
    return process_sell_buy

def start_cycleset_buy_sell(user_config):
    process_buy_sell = Process(target=create_and_start_cycle_set_buy_sell, args=(user_config,))
    process_buy_sell.name = 'cycleset_buy_sell'
    process_buy_sell.start()
    return process_buy_sell

def main():
    while True:
        # Prompt user to choose the type of cycle set
        print("Choose the type of cycle set to start:")
        print("1. Sell Buy Cycle Set")
        print("2. Buy Sell Cycle Set")
        print("3. Exit")
        choice = int(input("Enter your choice (1, 2, or 3): "))

        # Depending on user choice, collect user input for the corresponding cycle set
        if choice == 1:
            user_config = collect_sell_buy_input()
            target_function = create_and_start_cycle_set_sell_buy
        elif choice == 2:
            user_config = collect_buy_sell_input()
            target_function = create_and_start_cycle_set_buy_sell
        elif choice == 3:
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
            continue

        # Start a separate process for the selected cycle set
        process = Process(target=target_function, args=(user_config,))
        process.start()

if __name__ == "__main__":
    main()
