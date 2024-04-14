from flask import Flask, render_template,request
from flask_sqlalchemy import SQLAlchemy

app=Flask(__name__)

import config
import models, routes, api

if __name__ == '__main__':
  # Run the Flask app
  app.run()
















