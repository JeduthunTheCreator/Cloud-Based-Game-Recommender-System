from flask import Flask, request, Response
import pickle, json, jsonpickle
import pandas as pd
import traceback
import redis
import os
from math import sqrt
from flask import session
from redis_management import RedisConnections
import numpy as np

# Initialize the Flask application
app = Flask(__name__)

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


def initialize_application():
    global games_df, publishers_df
    try:
        # Load data
        genres_df = pd.read_csv("dataset/genres.csv")
        games_df = pd.read_csv("dataset/games.csv")
        publishers_df = pd.read_csv("dataset/publishers.csv")

        # Handle duplicates
        if publishers_df['id'].duplicated().any():
            publishers_df = publishers_df.drop_duplicates(subset='id', keep='first')

        # Initialize genres in Redis
        if not gen_db.llen("genres"):
            genres_set = set(genres_df['name'])  # Remove duplicates
            for genre in genres_set:
                gen_db.rpush("genres", genre)
            print("Genres loaded to DB0.")
        else:
            print("Genres list already in DB0.")

        # Prepare game dictionary
        latest_game_id = games_df['id'].max()
        gen_db.set("latest_game_id", int(latest_game_id))
        print("Latest game id:{}".format(latest_game_id))

        game_dict = {}
        publisher_dict = publishers_df.set_index('id').to_dict('index')
        genre_dict = genres_df.groupby('id')['name'].apply(list).to_dict()

        for _, row in games_df.iterrows():
            game_id = str(row['id'])
            game_name = row['name']
            rating = row['rating']

            img_url = publisher_dict.get(game_id, {}).get('image_background', 'default_url')
            game_genres = genre_dict.get(game_id, [])

            game_dict[game_id] = [game_name, img_url, "|".join(game_genres), rating]

        # Store in Redis
        game_db.set("game_dict", jsonpickle.dumps(game_dict))
        print("GameDB populated.")

    except Exception as e:
        print("Error initializing application: {}".format(str(e)))
        print(traceback.print_exc())



# route http posts to this method
@app.route('/compute/games/<userid>', methods=['POST'])
def compute_games(userid):
    try:
        if json.loads(gen_db.get(userid)).get('rate', False):
            print("/compute/games api call started")
            r = request
            genre_list = jsonpickle.loads(r.data)
            game_dict = json.loads(game_db.get("game_dict"))
            result = []
            for genre in genre_list:
                for game_id, details in game_dict.items():
                    if genre in details[2]:  # details[2] contains the genres string
                        result.append(game_id)
            game_list = []
            for game_id in set(result):
                genres = game_dict[game_id][2].split("|")
                game_list.append([game_id, list(set(genres) & set(genre_list))[0]])
            user_game_db.set(userid, jsonpickle.dumps(game_list))
            print('Game selection for rating updated.')
        else:
            print('No new computation required for user {} as genre selection unchanged.'.format(userid))

        response = {'status': 'OK'}

    except Exception as e:
        response = {'status': 'error'}
        print('Error during game computation:', traceback.format_exc())

    # encode response using jsonpickle
    response_pickled = jsonpickle.encode(response)
    return Response(response=response_pickled, status=200, mimetype="application/json")


@app.route('/compute/recommendations/<userid>', methods=['GET'])
def get_recommendations(userid):
    try:
        recommendations = json.loads(user_recc_db.get(userid) or '{}')
        if recommendations:
            return Response(json.dumps(recommendations), mimetype='application/json', status=200)
        else:
            return Response(json.dumps({"error": "No recommendations found"}), mimetype='application/json', status=404)
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), mimetype='application/json', status=500)


def compute_statistics(group, inputGames):
    # Calculate the sums and products needed for Pearson correlation
    temp_df = inputGames[inputGames['gameId'].isin(group['gameId'].tolist())]
    tempRatingList = temp_df['rating'].tolist()
    tempGroupList = group['rating'].tolist()
    nRatings = len(tempRatingList)

    Sxx = sum([i ** 2 for i in tempRatingList]) - pow(sum(tempRatingList), 2) / float(nRatings)
    Syy = sum([i ** 2 for i in tempGroupList]) - pow(sum(tempGroupList), 2) / float(nRatings)
    Sxy = sum(i * j for i, j in zip(tempRatingList, tempGroupList)) - sum(tempRatingList) * sum(tempGroupList) / float(
        nRatings)

    return Sxx, Syy, Sxy
    pass


def compute_pearson(Sxx, Syy, Sxy):
    # Calculate the Pearson correlation coefficient
    if Sxx != 0 and Syy != 0:
        return Sxy / sqrt(Sxx * Syy)
    else:
        return 0
    pass


def compute_recommendations_df(topUsers, ratings_df):
    # Create a DataFrame for the top users and compute weighted ratings
    topUsersRating = topUsers.merge(ratings_df, left_on='userId', right_on='userId', how='inner')
    topUsersRating['weightedRating'] = topUsersRating['similarityIndex'] * topUsersRating['rating']

    # Sum up the weighted ratings and the similarity indices
    tempTopUsersRating = topUsersRating.groupby('gameId').sum()[['similarityIndex', 'weightedRating']]
    tempTopUsersRating.columns = ['sum_similarityIndex', 'sum_weightedRating']

    # Compute weighted average recommendation scores
    recommendation_df = pd.DataFrame()
    recommendation_df['weighted average recommendation score'] = tempTopUsersRating['sum_weightedRating'] / \
                                                                 tempTopUsersRating['sum_similarityIndex']
    recommendation_df['gameId'] = tempTopUsersRating.index

    return recommendation_df.sort_values(by='weighted average recommendation score', ascending=False)
    pass


def store_recommendations(recommendation_df, userid):
    # Format recommendations into a list and store in Redis
    recc_list = []
    for index, row in recommendation_df.iterrows():
        recc_list.append({
            'gameId': row['gameId'],
            'score': row['weighted average recommendation score']
        })
    user_recc_db.set(userid, jsonpickle.dumps(recc_list))
    print("Recommendations stored for user:", userid)
    pass


# route http posts to this method
@app.route('/compute/recommendations/<userid>', methods=['POST'])
def compute_recommendations(userid):
    try:
        print("/compute/recommendations/ api call started")
        if json.loads(gen_db.get(userid)).get('recc', False):
            game_dict = jsonpickle.loads(game_db.get("game_dict"))
            user_ratings = jsonpickle.loads(active_user_rating_db.get(userid) or '{}')

            userInput = [{'title': game_dict[game_id][0], 'rating': rating[0]} for game_id, rating in user_ratings.items() if game_id in game_dict]
            inputGames = pd.DataFrame(userInput)

            userSubset = games_df[games_df['id'].isin(inputGames['id'].tolist())]
            userSubsetGroup = userSubset.groupby(['userId'])
            userSubsetGroup = sorted(userSubsetGroup, key=lambda x: len(x[1]), reverse=True)[:100]

            pearsonCorrelationDict = {}
            for name, group in userSubsetGroup:
                group = group.sort_values(by='id')
                inputGames = inputGames.sort_values(by='id')
                Sxx, Syy, Sxy = compute_statistics(group, inputGames)
                pearsonCorrelationDict[name] = compute_pearson(Sxx, Syy, Sxy)

            pearsonDF = pd.DataFrame.from_dict(pearsonCorrelationDict, orient='index')
            pearsonDF.columns = ['similarityIndex']
            topUsers = pearsonDF.sort_values(by='similarityIndex', ascending=False)[:50]
            recommendations = compute_recommendations_df(topUsers, games_df)

            store_recommendations(recommendations, userid)

            response = {'status': 'OK'}
            print("Recommendations computed and stored.")
        else:
            print('No new recommendations computed; user {} did not update ratings.'.format(userid))
            response = {'status': 'No new recommendations needed.'}

    except Exception as e:
        response = {'status': 'error'}
        print('Error during recommendation computation:', traceback.format_exc())

    response_pickled = jsonpickle.encode(response)
    return Response(response=response_pickled, status=200, mimetype="application/json")


print("Initializing application...")

initialize_application()

# start flask app
app.run(host="0.0.0.0", port=5000, debug=True)
