from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

@app.route("/health", methods=["GET"])
def health():
    return jsonify(dict(status="OK")), 200


@app.route("/count")
def count():
    """return length of data"""
    count = db.songs.count_documents({})
    if count is None:
        return {"message": "Internal server error"}, 500
    
    return jsonify(message=f"{count} songs available"), 200


@app.route("/song")
def songs():
    """Returns all songs in the songs collection, properly formatted as JSON without _id fields."""

    try:
        # Fetch all songs from the database
        all_songs = [song for song in db.songs.find({})]

        # Serialize all songs to JSON
        serialized_songs = [json.dumps(song, default=str) for song in all_songs]

        # Remove _id key-value pairs from each serialized song string
        songs_without_id = [json.loads(song) for song in serialized_songs]
        for song in songs_without_id:
            song.pop('_id', None)

        # Handle the case of no songs in the collection
        if not songs_without_id:
            return jsonify(message="No songs found"), 404

        # Return a well-formatted JSON response without _id fields
        return jsonify({"songs": songs_without_id}), 200

    except Exception as e:
        # Handle potential exceptions gracefully
        print(f"An error occurred while fetching songs: {e}")
        return jsonify(message="Internal server error"), 500


@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """Searches for song in db by id"""
    found_song = db.songs.find_one({"id":id})

    # Handles case for if id is not in db
    if found_song == None:
        return jsonify(message=f"song with id {id} not found"), 404
    
    return {"Search Result": f"{found_song}"}, 200


@app.route("/song", methods=["POST"])
def create_song():
    """Appends new song to song_list from request obj
    Handles cases for bad JSON data or duplicate song id
    """
    song_data = request.json
    
    if song_data is None:
        return {"Message": "Invalid JSON data"}, 404
    
    song_id = song_data["id"]
    # Check if the song ID already exists in the song_list
    song_exists = db.songs.find_one({"id": song_id})
    if song_exists:
        return {"Message": f"Song with id {song_id} already present"}, 302
    
    # Insert data to db
    result = db.songs.insert_one(song_data)
    if result:
        return {"Message": f"Song {song_id} added successfully"}, 201
    return {"message": "Internal server error"}, 500


@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """Updates a song by id from request obj
    Handles case for song id not found in db
    """
    song_data = request.json
    
    # check that update data is valid
    if song_data is None:
        return {"Message": "Invalid update data"}, 404

    # Update the song in the database
    result = db.songs.update_one({"id":id}, {"$set": song_data})

    if result.modified_count == 0:
        return jsonify(message=f"No song with id {id} found or nothing to update"), 404
    
    return jsonify(message=f"Song with id {id} updated successfully"), 200


@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """Fetches song by id and deletes song"""
    
    result = db.songs.delete_one({"id":id})

    if result.deleted_count == 1:
        return {}, 204
    return jsonify(message=f"song with id {id} not found")