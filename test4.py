# test3.py

# Import necessary modules and classes
from user_input2 import user_config
from starting_input import user_config
from cycle_set_utils import CycleSet, Cycle

starting_size = user_config["starting_size_Q"]
cycle_type = "buy-sell"

# Create cycle set
cycle_set = CycleSet(
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

# Start a cycle within the cycle set
cycle_set.start_buy_sell_starting_cycle(user_config)