from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped
from sqlalchemy import Integer, String, Float, Column, text, desc
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired, ValidationError
import requests
from flask import flash, session
from config import Config


app = Flask(__name__)
app.config.from_object(Config)

Bootstrap5(app)



# CREATE DB
class Base(DeclarativeBase):
    pass


# 建立 SQLAlchemy 物件 db，並將 Base 作為 model_class 參數傳遞給它
db = SQLAlchemy(model_class=Base)

# 初始化 SQLAlchemy 應用程式
db.init_app(app)


# CREATE TABLE
class Movie(db.Model):
    __tablename__ = "movies"
    id = Column(Integer,  primary_key=True)
    title = Column(String(250), unique=True, nullable=False)
    year = Column(Integer, nullable=False)
    description = Column(String(250), nullable=False)
    rating = Column(Float, nullable=False)
    ranking = Column(Integer, nullable=False)
    review = Column(String(250))
    img_url = Column(String(250))



class EditForm(FlaskForm):
    rating = FloatField("Your Rating Out of 10 e.g. 5.5")
    review = StringField("Your Review")
    submit = SubmitField("Done")
    back_to_home = SubmitField("Back to Home")

    def __init__(self, *args, **kwargs):
        super(EditForm, self).__init__(*args, **kwargs)
        self.back_to_home.label.text = 'Back to Home'

    def validate_back_to_home(self, field):
        # 如果按下 "Back to Home" 按鈕，直接返回 True，不进行验证
        if field.data:
            return True

    def validate_rating(self, field):
        # Check if the rating field is filled and is a float value
        if field.data:
            try:
                float(field.data)
            except ValueError:
                raise ValidationError('Rating must be a float value.')


class AddForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")
    back_to_home = SubmitField("Back to Home")

    def __init__(self, *args, **kwargs):
        super(AddForm, self).__init__(*args, **kwargs)
        self.back_to_home.label.text = 'Back to Home'

    def validate_back_to_home(self, field):
        # 如果按下 "Back to Home" 按鈕，直接返回 True，不进行验证
        if field.data:
            return True


@app.route("/")
def home():
    all_movies = Movie.query.order_by(desc(Movie.rating)).all()
    for i in range(len(all_movies)):
        all_movies[i].ranking = i+1
    db.session.commit()

    return render_template("index.html", all_movies=all_movies)


@app.route("/edit/<id>", methods=["GET", "POST"])
def edit(id):
    update_id = id
    update_movie = db.get_or_404(Movie, update_id)
    form = EditForm()
    if form.back_to_home.data:  # 检查是否点击了 "Back to Home" 按钮
        return redirect(url_for("home"))
    if form.validate_on_submit():
        update_movie.rating = form.rating.data
        update_movie.review = form.review.data
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("edit.html", form=form)


@app.route("/delete")
def delete():
    delete_id = request.args.get("id")
    delete_movie = db.get_or_404(Movie, delete_id)
    db.session.delete(delete_movie)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/add", methods=["GET", "POST"])
def add():
    form = AddForm()
    url = "https://api.themoviedb.org/3/search/movie"
    # 設定TMDB API端點和參數
    params = {
        "api_key": app.config["TMDB_API_KEY"],
        "query": form.title.data
    }
    # 發送GET請求
    if request.method == "POST":
        if form.back_to_home.data:
            return redirect(url_for('home'))
        response = requests.get(url, params=params)
    # 若有找到電影，解析回傳的JSON資料
        data = response.json()
        results = data["results"]
        return render_template("select.html", results=results)
    elif request.method == "GET":
        select_movie_id = request.args.get("id")
        if select_movie_id:
            headers = {
                "accept": "application/json",
                "Authorization": app.config["AUTHORIZATION"]
                    }
            select_movie = requests.get(f"https://api.themoviedb.org/3/movie/{select_movie_id}", headers=headers).json()
            existing_movie = Movie.query.filter_by(title=select_movie["title"]).first()
            if existing_movie:
                # 如果電影已存在，您可以採取適當的處理方式，例如更改電影標題或拒絕新增重複的電影
                # 在這個範例中，我們只是發出一個錯誤訊息並將用戶重定向至首頁
                flash("Movie already exists!")
                return redirect(url_for("add"))
            print(select_movie)

            new_movie = Movie(
                img_url=f"https://image.tmdb.org/t/p/w500{select_movie['poster_path']}",
                title=select_movie["title"],
                year=int(select_movie["release_date"][:4]),
                description=select_movie["overview"],
                rating=0,
                ranking=0,
                review=""
            )
            print(new_movie)
            db.session.add(new_movie)
            db.session.commit()
            return redirect(url_for("rate_movie", id=new_movie.id))
    return render_template("add.html", form=form)


@app.route("/edit", methods=["GET", "POST"])
def rate_movie():
    form = EditForm()
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    if form.back_to_home.data:  # 检查是否点击了 "Back to Home" 按钮
        return redirect(url_for("home"))
    if form.validate_on_submit():
        movie.rating = form.rating.data
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("edit.html", form=form)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # db.session.add(second_movie)
        # db.session.commit()
    app.run(debug=True)
