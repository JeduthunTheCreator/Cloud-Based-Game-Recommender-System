import streamlit as st
import traceback
import hashlib
import os
import json, jsonpickle
import requests
from redis_management import RedisConnections

# streamlit page settings
st.set_page_config(layout="wide")
page_bg_img = '''
<style>
body {
background-image: url("https://www.google.com/url?sa=i&url=https%3A%2F%2Fwww.canva.com%2Fdesktop-wallpapers%2Ftemplates%2Fgaming%2F&psig=AOvVaw2XwihG5T5Vpz70WxB_f46u&ust=1714218950422000&source=images&cd=vfe&opi=89978449&ved=0CBIQjRxqFwoTCMiKk7Xp34UDFQAAAAAdAAAAABAE");
background-size: cover;
}
</style>
'''
st.markdown(page_bg_img, unsafe_allow_html=True)

# Environment and Redis setup
redis_host = os.getenv("REDIS_HOST", "localhost")
rest_host = os.getenv("REST", "127.0.0.1:5000")
addr = f"http://{rest_host}"
redis_conns = RedisConnections(redis_host)

# Usage example:
gen_db = redis_conns.get_db(0)
login_db = redis_conns.get_db(1)
active_user_rating_db = redis_conns.get_db(2)
game_db = redis_conns.get_db(3)
user_game_db = redis_conns.get_db(4)
user_recc_db = redis_conns.get_db(5)


def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text


def render_game_list(login_userid, start_index, rec_dict):
    total_games = 24  # Define how many games to display at a time
    game_dict = json.loads(game_db.get("game_dict") or "{}")
    user_game_list = json.loads(user_game_db.get(login_userid) or "[]")
    games_to_display = user_game_list[start_index:start_index + total_games]

    for idx, game_info in enumerate(games_to_display):
        game_id = str(game_info[0])
        genre = game_info[1]
        game_details = game_dict.get(game_id, {"gameName": "Unknown", "ImageUrl": "", "year": "N/A"})
        game_name = game_details.get('gameName', 'Unknown')

        if idx % 6 == 0:
            cols = st.columns(6)

        with cols[idx % 6]:
            st.image(game_details['ImageUrl'], width=100, caption=game_name)
            rating = st.slider("Rating", 0.0, 5.0, value=float(rec_dict.get(game_id, [0.0])[0]), step=0.5, key=f"rating_{game_id}")
            rec_dict[game_id] = [rating, genre]

    if st.button("Submit Ratings"):
        active_user_rating_db.set(login_userid, jsonpickle.encode(rec_dict))
        st.success("Ratings updated successfully.")


def display_rated_games():
    """Display games that the logged-in user has rated."""
    if 'user_id' not in st.session_state or not st.session_state['user_id']:
        st.error("User not logged in. Please log in to view rated games.")
        return

    login_userid = st.session_state['user_id']
    user_data_json = active_user_rating_db.get(login_userid)
    if not user_data_json:
        st.write("No games rated yet.")
        return

    rec_dict = json.loads(user_data_json)
    game_dict_json = game_db.get("game_dict")
    if not game_dict_json:
        st.error("Game details are currently unavailable.")
        return

    game_dict = json.loads(game_dict_json)
    game_id_list = list(rec_dict.keys())
    total_games = len(game_id_list)

    if total_games > 0:
        for game_id in game_id_list:
            game_details = game_dict.get(game_id, {})
            game_name = game_details.get('gameName', 'Unknown')
            game_img = game_details.get('ImageUrl', '')
            rating = float(rec_dict[game_id][0])
            genre = rec_dict[game_id][1]

            cols = st.columns(6)
            with cols[0]:
                st.image(game_img, width=100, caption=game_name)
                st.write(f"{game_name} ({genre}) Rated: {rating}")
    else:
        st.write("No games rated yet.")


def get_game_recommendations():
    """Fetch game recommendations for the logged-in user."""
    if 'user_id' not in st.session_state or not st.session_state['user_id']:
        st.warning("Please log in to view recommendations.")
        return

    user_id = st.session_state['user_id']
    try:
        response = requests.get(f"{addr}/compute/recommendations/{user_id}")
        if response.status_code == 200:
            recommendations = response.json()
            if recommendations:
                st.subheader("Your Game Recommendations")
                for rec in recommendations:
                    st.write(f"Recommended: {rec['title']} - {rec['match_percent']}% match")
            else:
                st.write("No recommendations available at the moment.")
        else:
            st.error(f"Failed to fetch recommendations: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while fetching recommendations: {str(e)}")


def main():
    st.title("Game Recommender System")
    menu = ["Home", "Login", "SignUp", "Logout"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Home":
        st.subheader("Home")
        if st.session_state.get('logged_in'):
            if st.button("Show Rated Games"):
                display_rated_games()
            if st.button("Get Recommendations"):
                get_game_recommendations()

    elif choice == "Login":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type='password')
        if st.sidebar.button("Login"):
            user_data = login_db.hgetall(username)
            if user_data and check_hashes(password, user_data['password']):
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user_data['user_id']
                st.success(f"Logged in as {username}")

    elif choice == "SignUp":
        new_user = st.text_input("New Username")
        new_password = st.text_input("New Password", type='password')
        if st.button("Signup"):
            if not login_db.exists(new_user):
                user_id = login_db.incr('latest_user_id')
                login_db.hset(new_user, mapping={'password': make_hashes(new_password), 'user_id': user_id})
                st.success("Account created. You can now log in.")
            else:
                st.error("Username already exists.")

    elif choice == "Logout":
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Logged out successfully.")


if __name__ == '__main__':
    main()
