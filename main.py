import random
from collections import Counter
import streamlit as st
from openai import OpenAI
import os

class PokerOddsCalculator:
    def __init__(self, simulations=10000):
        self.simulations = simulations
        self.deck = ['2h', '3h', '4h', '5h', '6h', '7h', '8h', '9h', 'Th', 'Jh', 'Qh', 'Kh', 'Ah',
                    '2d', '3d', '4d', '5d', '6d', '7d', '8d', '9d', 'Td', 'Jd', 'Qd', 'Kd', 'Ad',
                    '2s', '3s', '4s', '5s', '6s', '7s', '8s', '9s', 'Ts', 'Js', 'Qs', 'Ks', 'As',
                    '2c', '3c', '4c', '5c', '6c', '7c', '8c', '9c', 'Tc', 'Jc', 'Qc', 'Kc', 'Ac']
        self.value_order = "23456789TJQKA"
        self.value_ranks = {v: i for i, v in enumerate(self.value_order)}

    def calculate_odds(self, board_cards, n_cards):
        deck = list(self.deck)
        for card in board_cards:
            deck.remove(card)

        counts = {
            "no_hand": 0,
            "pair": 0,
            "two_pair": 0,
            "trips": 0,
            "straight": 0,
            "flush": 0,
            "full_house": 0,
            "four_of_a_kind": 0,
            "straight_flush": 0,
            "royal_flush": 0
        }

        for _ in range(self.simulations):
            sampled_deck = random.sample(deck, n_cards)
            current_hand = board_cards + sampled_deck
            hand_rank = self.evaluate_hand(current_hand)

            if hand_rank is None:
                counts["no_hand"] += 1
            else:
                counts[hand_rank] += 1

        odds = {k: (v / self.simulations) * 100 for k, v in counts.items()}
        return odds

    def evaluate_hand(self, hand):
        def is_straight(values):
            sorted_indices = sorted(set([self.value_ranks[v] for v in values]))
            if len(sorted_indices) < 5:
                return False
            for i in range(len(sorted_indices) - 4):
                if sorted_indices[i:i+5] == list(range(sorted_indices[i], sorted_indices[i]+5)):
                    return True
            return False

        def is_flush(suits):
            suit_counts = Counter(suits)
            for suit, count in suit_counts.items():
                if count >= 5:
                    return True
            return False

        def get_flush_suit(suits):
            suit_counts = Counter(suits)
            for suit, count in suit_counts.items():
                if count >= 5:
                    return suit
            return None

        def get_straight_flush(values, suits):
            flush_suit = get_flush_suit(suits)
            if flush_suit:
                flush_cards = [card[0] for card in hand if card[1] == flush_suit]
                if is_straight(flush_cards):
                    return True
            return False

        values = [card[0] for card in hand]
        suits = [card[1] for card in hand]
        multiples = Counter(values)

        straight = is_straight(values)
        flush = is_flush(suits)
        straight_flush = get_straight_flush(values, suits)

        if straight_flush:
            if set(values) >= set(self.value_order[-5:]):
                return "royal_flush"
            return "straight_flush"
        if 4 in multiples.values():
            return "four_of_a_kind"
        if 3 in multiples.values() and 2 in multiples.values():
            return "full_house"
        if flush:
            return "flush"
        if straight:
            return "straight"
        if 3 in multiples.values():
            return "trips"
        if list(multiples.values()).count(2) == 2:
            return "two_pair"
        if 2 in multiples.values():
            return "pair"

        return None

def card_emoji(card):
    value = card[0]
    suit = card[1]
    suits = {'h': '🧡', 'd': '♦️', 's': '♠️', 'c': '♣️'}
    return f"{value}{suits[suit]}"

# OpenAI API 설정
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Streamlit App

st.title("Poker Odds Calculator")

# Input fields for seed money and current balance
seed_money = st.number_input('Seed Money : 처음에 모두가 갖고 시작하는 금액이 얼마인지', min_value=0, step=1000, value = 10000)
current_balance = st.number_input('My Money : 현재 내가 갖고 있는 금액', min_value=0, step=1000, value = 12000)

# Input field for current call amount
current_call = st.number_input('Current Call Amount : 현재 콜을 받기 위해 지불해야 하는 금액', min_value=0, step=100, value = 1000)

poker_calculator = PokerOddsCalculator()

if 'selected_cards' not in st.session_state:
    st.session_state.selected_cards = []

if 'card_counters' not in st.session_state:
    st.session_state.card_counters = {card: 0 for card in poker_calculator.deck}

# Count the number of turns based on "✅" and extract hand and field cards
turn_count_raw = sum(1 for card in st.session_state.card_counters if st.session_state.card_counters[card] % 3 == 1)
hand_cards = [card for card, count in st.session_state.card_counters.items() if count % 3 == 2]
field_cards = [card for card, count in st.session_state.card_counters.items() if count % 3 == 1]

if turn_count_raw == 0:
    turn_count = "Pre-flop"
elif turn_count_raw == 3:
    turn_count = "Flop"
elif turn_count_raw == 4:
    turn_count = "Turn"
elif turn_count_raw == 5:
    turn_count = "River"
else:
    turn_count = f"Unknown stage with {turn_count_raw} turns"

if st.session_state.selected_cards:
    probabilities = poker_calculator.calculate_odds(st.session_state.selected_cards, 7 - len(st.session_state.selected_cards))
    probabilities_text = "\n".join([f"{hand.capitalize()}: {prob:.2f}%" for hand, prob in probabilities.items()])
else:
    probabilities_text = "No probabilities calculated."

# Display GPT-4 advice button and output at the top
if st.button('Get Advice from GPT-4'):
    hand_message = " and ".join(hand_cards) if hand_cards else "no cards"
    field_message = " / ".join(field_cards) if field_cards else "no cards"

    message = f"""I am currently playing Texas hold 'em. \n
    Here are the odds for my hand: {probabilities_text} \n
    I started with a seed bankroll of {seed_money}. \n
    Initially I was dealt two hands, {hand_message}. \n
    The field is now dealt cards, {field_message}. \n
    Now {turn_count} turns have passed. \n
    It's my turn to bet. I currently have {current_balance} and need {current_call} to make a call. \n
    Which choice should I make? \n
    Should I fold? Should I call? If I should bet, how much more should I bet? \n
    Please give me a simple and short answer and answer in Korean. \n
    I prefer betting. \n
    Don't be vague and give me a single decision. Even if you place additional bets, calculate the exact amount. With a reason."""

    # GPT-4 API 호출
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message},
        ]
    )
    # st.write(f"현재 카드 현황: 핸드: {hand_message}, 필드: {field_message}, 현재 턴 수: {turn_count}")
    # st.write(response.choices[0].message.content)
    st.session_state['advice'] = response.choices[0].message.content
    st.session_state['hand_message'] = hand_message
    st.session_state['field_message'] = field_message
    st.session_state['turn_count'] = turn_count

# Display the saved advice if available
if 'advice' in st.session_state:
    st.write(f"현재 카드 현황: 핸드: {st.session_state['hand_message']}, 필드: {st.session_state['field_message']}, 현재 턴 수: {st.session_state['turn_count']}")
    st.write(st.session_state['advice'])

# Display the rest of the UI below
if st.session_state.selected_cards:
    st.subheader('Poker Odds:')
    col1, col2 = st.columns(2)
    with col1:
        for hand in list(probabilities.keys())[:5]:
            st.write(f"{hand.capitalize()}: {probabilities[hand]:.2f}%")
    with col2:
        for hand in list(probabilities.keys())[5:]:
            st.write(f"{hand.capitalize()}: {probabilities[hand]:.2f}%")
else:
    st.write("Please select cards to calculate odds.")


st.subheader('Select your cards (up to 7) + 한 번 클릭: 필드에 있는 카드, 두 번 클릭: 나의 핸드(패) 카드, 세 번 클릭: 선택 취소')
cols = st.columns(13)
for i, card in enumerate(poker_calculator.deck):
    col = cols[i % 13]
    card_label = card_emoji(card)
    counter = st.session_state.card_counters[card]

    if card in st.session_state.selected_cards:
        if counter % 3 == 1:
            button_label = f"✅ {card_label}"
        elif counter % 3 == 2:
            button_label = f"🂫 {card_label}"
        else:
            button_label = card_label
    else:
        button_label = card_label

    if col.button(button_label, key=f"{card}_btn", use_container_width=True):
        st.session_state.card_counters[card] += 1
        if st.session_state.card_counters[card] % 3 == 1:
            if card not in st.session_state.selected_cards and len(st.session_state.selected_cards) < 7:
                st.session_state.selected_cards.append(card)
        elif st.session_state.card_counters[card] % 3 == 0:
            if card in st.session_state.selected_cards:
                st.session_state.selected_cards.remove(card)
        st.rerun()

if st.button('Reset'):
    st.session_state.selected_cards = []
    st.session_state.card_counters = {card: 0 for card in poker_calculator.deck}
    st.rerun()

