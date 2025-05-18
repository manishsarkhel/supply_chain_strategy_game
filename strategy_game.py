import streamlit as st
import random

# --- Game Configuration ---
MAX_ROUNDS = 12
INITIAL_CASH = 50000
INITIAL_INVENTORY = 100
INITIAL_SATISFACTION = 80
HOLDING_COST_PER_UNIT = 2
STOCKOUT_PENALTY_PER_UNIT = 30 # Represents lost profit, goodwill, etc.
SELLING_PRICE_PER_UNIT = 50
DEMAND_RANGE = (80, 220) # Min and max demand per round
LOW_SATISFACTION_THRESHOLD = 30 # Game over if satisfaction drops to this or below
BANKRUPTCY_THRESHOLD = 0 # Game over if cash drops to this or below

# Supplier Options: Name: (cost_per_unit, yield_options_weights, yield_percentages)
# yield_options_weights: probability of each yield outcome
# yield_percentages: actual yield percentage for each outcome
SUPPLIERS = {
    "Alpha Goods (Reliable & Pricey)": {
        "cost": 20,
        "yield_weights": [1.0], # 100% chance
        "yield_percentages": [1.0] # of 100% yield
    },
    "Beta Stock (Standard)": {
        "cost": 15,
        "yield_weights": [0.9, 0.1], # 90% chance, 10% chance
        "yield_percentages": [1.0, 0.7] # of 100% yield, of 70% yield
    },
    "Gamma Source (Cheap & Risky)": {
        "cost": 10,
        "yield_weights": [0.6, 0.3, 0.1], # 60%, 30%, 10%
        "yield_percentages": [1.0, 0.5, 0.2] # of 100%, 50%, 20% yield
    }
}

# Transportation Options: Name: (cost_per_procured_unit, disruption_chance, disruption_cost, damage_chance, damage_percentage)
TRANSPORTERS = {
    "Express Freight (Fast & Secure)": {
        "cost": 8,
        "disruption_chance": 0.05,
        "disruption_fee": 200,
        "damage_chance": 0.01, # Chance of goods getting damaged
        "damage_percentage": 0.05 # Percentage of goods lost if damaged
    },
    "Standard Shipping (Balanced)": {
        "cost": 5,
        "disruption_chance": 0.15,
        "disruption_fee": 150,
        "damage_chance": 0.03,
        "damage_percentage": 0.10
    },
    "Budget Haul (Slow & Risky)": {
        "cost": 3,
        "disruption_chance": 0.30,
        "disruption_fee": 100,
        "damage_chance": 0.05,
        "damage_percentage": 0.15
    }
}

# --- Helper Functions ---
def initialize_game():
    """Sets up the initial game state."""
    st.session_state.round = 1
    st.session_state.cash = INITIAL_CASH
    st.session_state.inventory = INITIAL_INVENTORY
    st.session_state.satisfaction = INITIAL_SATISFACTION
    st.session_state.total_costs_accumulated = 0
    st.session_state.game_over = False
    st.session_state.game_over_message = ""
    st.session_state.history = [] # To store data for charts
    st.session_state.round_events = [] # Messages for the player per round

def get_supplier_details(name):
    return SUPPLIERS[name]

def get_transport_details(name):
    return TRANSPORTERS[name]

def simulate_round(supplier_name, quantity_ordered, transport_name):
    """Simulates one round of the game based on player decisions."""
    st.session_state.round_events = [] # Clear previous round events

    supplier = get_supplier_details(supplier_name)
    transporter = get_transport_details(transport_name)

    # 1. Calculate Procured Quantity & Sourcing Cost
    chosen_yield_percentage = random.choices(supplier["yield_percentages"], weights=supplier["yield_weights"], k=1)[0]
    procured_quantity = int(quantity_ordered * chosen_yield_percentage)
    sourcing_cost = procured_quantity * supplier["cost"]

    if chosen_yield_percentage < 1.0:
        st.session_state.round_events.append(f"⚠️ Supplier '{supplier_name}' only provided {int(chosen_yield_percentage*100)}% of your order ({procured_quantity}/{quantity_ordered} units).")
    else:
        st.session_state.round_events.append(f"✅ Supplier '{supplier_name}' successfully provided all {procured_quantity} ordered units.")


    # 2. Calculate Transportation Cost & Apply Transport Disruption
    transport_cost_base = procured_quantity * transporter["cost"]
    final_transport_cost = transport_cost_base
    actual_received_quantity = procured_quantity

    if random.random() < transporter["disruption_chance"]:
        final_transport_cost += transporter["disruption_fee"]
        st.session_state.round_events.append(f"💸 Transport Disruption! A ${transporter['disruption_fee']} fee was applied for '{transport_name}'.")

    if random.random() < transporter["damage_chance"] and actual_received_quantity > 0 :
        damaged_units = int(actual_received_quantity * transporter["damage_percentage"])
        actual_received_quantity -= damaged_units
        st.session_state.round_events.append(f"💔 Transport Damage! {damaged_units} units were damaged using '{transport_name}'. Received {actual_received_quantity} units.")


    # 3. Update Available Inventory
    inventory_at_fulfillment = st.session_state.inventory + actual_received_quantity

    # 4. Generate Demand
    current_demand = random.randint(DEMAND_RANGE[0], DEMAND_RANGE[1])
    st.session_state.round_events.append(f"Demand this month: {current_demand} units.")

    # 5. Fulfill Demand
    units_sold = min(inventory_at_fulfillment, current_demand)
    revenue = units_sold * SELLING_PRICE_PER_UNIT
    unmet_demand = current_demand - units_sold

    if unmet_demand > 0:
        st.session_state.round_events.append(f"📉 Stockout! Could not meet {unmet_demand} units of demand.")
        st.session_state.satisfaction -= unmet_demand * 2 # Higher penalty for stockouts
        st.balloons() # A little negative feedback
    else:
        st.session_state.round_events.append(f"👍 All demand met! Sold {units_sold} units.")
        st.session_state.satisfaction += 5 # Bonus for meeting all demand
    
    st.session_state.satisfaction = max(0, min(100, st.session_state.satisfaction)) # Cap satisfaction

    # 6. Calculate Stockout Cost
    stockout_cost = unmet_demand * STOCKOUT_PENALTY_PER_UNIT

    # 7. Calculate Holding Cost
    ending_inventory = inventory_at_fulfillment - units_sold
    holding_cost = ending_inventory * HOLDING_COST_PER_UNIT

    # 8. Update Game State
    round_total_cost = sourcing_cost + final_transport_cost + stockout_cost + holding_cost
    st.session_state.cash += revenue - round_total_cost
    st.session_state.inventory = ending_inventory
    st.session_state.total_costs_accumulated += round_total_cost

    # Store history for this round
    st.session_state.history.append({
        "Round": st.session_state.round,
        "Cash": st.session_state.cash,
        "Inventory": st.session_state.inventory,
        "Satisfaction": st.session_state.satisfaction,
        "Demand": current_demand,
        "Procured": procured_quantity,
        "Received (after damage)": actual_received_quantity,
        "Sold": units_sold,
        "Stockout Units": unmet_demand,
        "Sourcing Cost": sourcing_cost,
        "Transport Cost": final_transport_cost,
        "Holding Cost": holding_cost,
        "Stockout Cost": stockout_cost,
        "Round Total Cost": round_total_cost,
        "Revenue": revenue
    })

    # 9. Check Game Over Conditions
    if st.session_state.cash <= BANKRUPTCY_THRESHOLD:
        st.session_state.game_over = True
        st.session_state.game_over_message = "Game Over: Bankruptcy! Your company ran out of cash."
    elif st.session_state.satisfaction <= LOW_SATISFACTION_THRESHOLD:
        st.session_state.game_over = True
        st.session_state.game_over_message = f"Game Over: Customer Exodus! Satisfaction dropped to {st.session_state.satisfaction}%."
    elif st.session_state.round >= MAX_ROUNDS:
        st.session_state.game_over = True
        st.session_state.game_over_message = "Game Over: End of Term! You've completed 12 months."

    # Increment round if game is not over
    if not st.session_state.game_over:
        st.session_state.round += 1


# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("🏭 Supply Chain Strategy Simulator 📈")
st.markdown("Manage your company's supply chain for 12 months. Make wise decisions on sourcing, ordering, and transportation to maximize profits and customer satisfaction!")

# Initialize game if not already done
if 'round' not in st.session_state:
    initialize_game()

# --- Game Over Screen ---
if st.session_state.game_over:
    st.header("🏁 Game Over  ")
    st.subheader(st.session_state.game_over_message)

    final_score = st.session_state.cash + (st.session_state.satisfaction * 100) - (st.session_state.total_costs_accumulated / 10)
    st.metric("Final Score (Cash + Satisfaction*100 - TotalCosts/10)", f"{final_score:,.0f}")
    
    st.write("---")
    st.subheader("Performance Summary:")
    col1, col2, col3 = st.columns(3)
    col1.metric("Final Cash Balance", f"${st.session_state.cash:,.0f}")
    col2.metric("Final Customer Satisfaction", f"{st.session_state.satisfaction}%")
    col3.metric("Total Costs Accumulated", f"${st.session_state.total_costs_accumulated:,.0f}")

    st.write("---")
    st.subheader("Performance Over Time:")
    
    # Prepare data for charts
    history_df = st.session_state.history # Already a list of dicts, good for st.line_chart
    
    # Filter history_df to only include numeric columns for charts
    # Extracting data for charts
    rounds = [h['Round'] for h in history_df]
    cash_data = [h['Cash'] for h in history_df]
    inventory_data = [h['Inventory'] for h in history_df]
    satisfaction_data = [h['Satisfaction'] for h in history_df]
    total_cost_data = [h['Round Total Cost'] for h in history_df] # Per round cost

    chart_data = {
        "Round": rounds,
        "Cash": cash_data,
        "Inventory": inventory_data,
        "Satisfaction": satisfaction_data,
        "Round Total Cost": total_cost_data
    }
    
    import pandas as pd # Import pandas for easier chart data handling
    chart_df = pd.DataFrame(chart_data).set_index("Round")


    st.line_chart(chart_df[["Cash", "Inventory", "Satisfaction"]])
    st.line_chart(chart_df[["Round Total Cost"]])
    
    st.write("---")
    st.subheader("Detailed Round History:")
    # Display history as a table, converting list of dicts to DataFrame
    detailed_history_df = pd.DataFrame(st.session_state.history)
    st.dataframe(detailed_history_df.set_index("Round"))


    if st.button("🔁 Play Again?"):
        initialize_game()
        st.rerun() # Use st.rerun for newer Streamlit versions
    
else:
    # --- Game In Progress ---
    st.sidebar.header(f"Month: {st.session_state.round} of {MAX_ROUNDS}")
    st.sidebar.metric("💰 Cash", f"${st.session_state.cash:,.0f}")
    st.sidebar.metric("📦 Current Inventory", f"{st.session_state.inventory} units")
    st.sidebar.metric("😊 Customer Satisfaction", f"{st.session_state.satisfaction}%")
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Previous Month's Demand (if applicable):** {st.session_state.history[-1]['Demand'] if st.session_state.history else 'N/A'}")


    st.subheader(f"Month {st.session_state.round}: Make Your Decisions")

    with st.form("decision_form"):
        st.markdown("####  Supplier Selection")
        supplier_choice = st.radio(
            "Choose your supplier for this month:",
            options=list(SUPPLIERS.keys()),
            format_func=lambda x: f"{x} (Cost: ${SUPPLIERS[x]['cost']}/unit)",
            help="Consider the trade-off between cost and reliability (yield)."
        )

        st.markdown("#### Order Quantity")
        quantity_to_order = st.number_input(
            "How many units to order this month?",
            min_value=0,
            max_value=1000, # Arbitrary max, can adjust
            value=max(0, int(DEMAND_RANGE[0] + (DEMAND_RANGE[1]-DEMAND_RANGE[0])/2 - st.session_state.inventory)), # Suggest a value based on avg demand & current inv
            step=10,
            help="Order enough to meet expected demand, considering current inventory and supplier reliability."
        )

        st.markdown("#### Transport (Transportation Mode)")
        transport_choice = st.radio(
            "Choose your transportation mode for this month's order:",
            options=list(TRANSPORTERS.keys()),
            format_func=lambda x: f"{x} (Cost: ${TRANSPORTERS[x]['cost']}/unit, Disruption: {TRANSPORTERS[x]['disruption_chance']*100}%)",
            help="Balance transport cost with speed and risk of disruption or damage."
        )

        submit_button = st.form_submit_button(label="➡️ Finalize Decisions & Proceed to Next Month")

    if submit_button:
        simulate_round(supplier_choice, quantity_to_order, transport_choice)
        # The game state (including game_over) is updated in simulate_round
        # Streamlit will automatically rerun and either show next round or game over screen
        st.rerun() # Use st.rerun for newer Streamlit versions

    st.markdown("---")
    st.subheader("📢 Last Month's Events & Outcomes:")
    if not st.session_state.round_events and st.session_state.round == 1:
        st.info("Make your first set of decisions to start the simulation!")
    elif not st.session_state.round_events and st.session_state.round > 1:
         st.info("No significant events to report from the previous turn, or waiting for your next decision.")
    for event in st.session_state.round_events:
        if "⚠️" in event or "💸" in event or "💔" in event or "📉" in event :
            st.warning(event)
        elif "✅" in event or "👍" in event:
            st.success(event)
        else:
            st.info(event)
    
    if st.session_state.history:
        st.markdown("---")
        st.markdown("#### Previous Month's Key Figures:")
        last_round_data = st.session_state.history[-1]
        
        col_figures1, col_figures2, col_figures3, col_figures4 = st.columns(4)
        col_figures1.metric("Units Sold", last_round_data['Sold'])
        col_figures2.metric("Revenue", f"${last_round_data['Revenue']:,.0f}")
        col_figures3.metric("Round Costs", f"${last_round_data['Round Total Cost']:,.0f}")
        col_figures4.metric("Stockout Units", last_round_data['Stockout Units'])

        col_details1, col_details2, col_details3, col_details4 = st.columns(4)
        col_details1.info(f"Sourcing: ${last_round_data['Sourcing Cost']:,.0f}")
        col_details2.info(f"Transport: ${last_round_data['Transport Cost']:,.0f}")
        col_details3.info(f"Holding: ${last_round_data['Holding Cost']:,.0f}")
        col_details4.info(f"Stockout Penalty: ${last_round_data['Stockout Cost']:,.0f}")


# Add a small footer
st.markdown("---")
st.markdown("Supply Chain Game v0.1 - A simple simulator.")

 