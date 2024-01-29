# test6.py
from starting_input import user_config
from cycle_set_utils import CycleSet, Cycle

# Define argument parameters
open_size_B = 100.0
open_price_sell = 0.112

# Create a CycleSet instance (assuming your CycleSet class has an __init__ method)
starting_size = user_config["starting_size_B"]
cycle_type = "sell_buy"
cycle_set_instance = CycleSet(
                    user_config["product_id"],
                    starting_size,
                    user_config["profit_percent"],
                    user_config["taker_fee"],
                    user_config["maker_fee"],
                    user_config["compound_percent"],
                    user_config["compounding_option"],
                    user_config["wait_period_unit"],
                    user_config["first_order_wait_period"],
                    user_config["chart_interval"],
                    user_config["num_intervals"],
                    user_config["window_size"],
                    user_config["stacking"],
                    user_config["step_price"],
                    cycle_type=cycle_type
                )

# Create a Cycle instance (assuming your Cycle class has an __init__ method)
sell_buy_cycle_instance, cycle_set_instance.cycle_number = cycle_set_instance.add_cycle(open_size_B, "sell_buy")

sell_buy_cycle_instance.cycle_number = cycle_set_instance.cycle_number
print(f"Starting next sell_buy cycle, Cycle {sell_buy_cycle_instance.cycle_number} of CycleSet {cycle_set_instance.cycleset_number} {cycle_set_instance.cycle_type}")


# Call the method on the instance
cycle_set_instance.place_next_sell_buy_cycle_orders(open_size_B, open_price_sell, sell_buy_cycle_instance)
