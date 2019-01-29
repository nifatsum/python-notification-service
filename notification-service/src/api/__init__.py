from flask import Flask, jsonify, abort, make_response, request, Response
from flask_restful import Api, Resource, reqparse, fields, marshal
from flask_httpauth import HTTPBasicAuth
import src.entities as orm
from src.message_rpc_client import MessageRpcClient, CallbackProcessingError
rpc_client = MessageRpcClient(auto_start=True)
auth = HTTPBasicAuth()
