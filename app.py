from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import logging
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from awsxray.ext.opentelemetry_utils import initialize_from_env
import requests

LOGFILE_NAME = "/var/log/app.log"

dburl = os.environ['RDS_ENDPOINT']
app = Flask(__name__)

# CloudWatch設定
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(LOGFILE_NAME)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
app.logger.addHandler(fh)

# OpenTelemetry Traceプロバイダーを初期化
provider = TracerProvider()
processor = BatchSpanProcessor()
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# AWS X-Rayエクスポーターを初期化
initialize_from_env()

# Flaskインストルメンテーションを有効化
FlaskInstrumentor().instrument_app(app)

# SQLAlchemyインストルメンテーションを有効化
SQLAlchemyInstrumentor().instrument(engine=db.engine)

# Database設定
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://Admin:password@{dburl}/taskdb"
# db = SQLAlchemy(app)
db=SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))


@app.route("/", methods=["GET", "POST"])
def home():
    todo_list = Todo.query.all()
    return render_template("index.html", todo_list=todo_list)

@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title")
    new_todo = Todo(title=title)
    db.session.add(new_todo)
    db.session.commit()
    app.logger.info(f'add task "{title}"')
    return redirect(url_for("home"))


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete(todo_id):
    todo = Todo.query.filter_by(id=todo_id).first()
    db.session.delete(todo)
    db.session.commit()
    app.logger.info(f'delete task "{todo}"')
    return redirect(url_for("home"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False,host='0.0.0.0', port=8080, threaded=True)
