from flask import Flask, Blueprint, request

index_pb = Blueprint('index_api', __name__)


@index_pb.route('/index')
def index():
    return "pass"
