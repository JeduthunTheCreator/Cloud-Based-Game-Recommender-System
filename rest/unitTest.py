import json
import unittest
import logging
from turtle import st

from GamesUplay import game_db

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def fetch_game_dict():
    try:
        game_dict_json = game_db.get("game_dict")
        if game_dict_json:
            logging.debug("Game dictionary fetched successfully.")
            return json.loads(game_dict_json)
        else:
            logging.error("Game dictionary is empty or not found.")
            return None
    except Exception as e:
        logging.error(f"Error fetching game dictionary: {str(e)}")
        return None


def display_rated_games():
    game_dict = fetch_game_dict()
    if not game_dict:
        st.error("Failed to load game details. Please check system logs or retry.")
        return


class TestDataLoading(unittest.TestCase):
    def test_game_dict_loading(self):
        game_dict = fetch_game_dict()
        self.assertIsNotNone(game_dict, "Game dictionary should not be None")
        self.assertTrue(isinstance(game_dict, dict), "Game dictionary should be a dictionary")
        self.assertGreater(len(game_dict), 0, "Game dictionary should not be empty")

if __name__ == '__main__':
    unittest.main()
