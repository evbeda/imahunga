import flask
import json
import bson.objectid as bson
import datetime


def json_serial(obj):

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, bson.ObjectId):
        return str(obj)
    raise TypeError("Type %s not serializable" % type(obj))


def init(app):
    @app.route('/ds/api/', methods=['GET'])
    def verify_number():
        member_number = flask.request.args.get('CardId')
        if len(member_number) != 16 or int(member_number) % 2 != 0:
            response = {
                "ERROR": -1
            }
            return json.dumps(response, default=json_serial)
        else:
            response = {
                "Kartentyp": "2",
                "Version": "00"
            }
            return json.dumps(response, default=json_serial)
