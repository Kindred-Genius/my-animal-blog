from typing import List
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, mapped_column, Mapped
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentPostForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

def admin_only(function):
    def wrap_function(*args, **kwargs):
        if current_user.id == 1:
            return function(*args, **kwargs)
        else:
            abort(403)

    wrap_function.__name__ = function.__name__
    return wrap_function


##CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "user_table"
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    authenticated = db.Column(db.Boolean, default=False)
    posts: Mapped["BlogPost"] = relationship(back_populates="author")
    comments: Mapped["BlogComment"] = relationship(back_populates="author")

    def is_active(self):
        """True, as all users are active."""
        return True

    def get_id(self):
        """Return the email address to satisfy Flask-Login's requirements."""
        return self.id

    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return self.authenticated

    def is_anonymous(self):
        """False, as anonymous users aren't supported."""
        return False


class BlogPost(db.Model):
    __tablename__ = "blog_posts_table"
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    author: Mapped[List["User"]] = relationship(back_populates="posts")
    author_id: Mapped[int] = mapped_column(db.ForeignKey("user_table.id"))
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments: Mapped["BlogComment"] = relationship(back_populates="post")


class BlogComment(db.Model):
    __tablename__ = "blog_comment_table"
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    author_id: Mapped[int] = mapped_column(db.ForeignKey("user_table.id"))
    author: Mapped[List["User"]] = relationship(back_populates="comments")
    post_id: Mapped[int] = mapped_column(db.ForeignKey("blog_posts_table.id"))
    post: Mapped[List["BlogPost"]] = relationship(back_populates="comments")


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        is_user_exist = User.query.filter_by(email=form.email.data).first()
        if not is_user_exist:
            new_user = User(
                email=form.email.data,
                password=generate_password_hash(form.password.data),
                name=form.name.data,
                authenticated=True
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("get_all_posts"))
        else:
            flash('Error: This email is already in use, log in instead..')
            return redirect(url_for('login'))

    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            user.authenticated = True
            db.session.commit()
            login_user(user)
            return redirect(url_for("get_all_posts"))
        else:
            flash("Error: Login or Password invalid.")
            return redirect(url_for("login"))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    current_user.authenticated = False
    db.session.commit()
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form = CommentPostForm()
    if form.validate_on_submit():
        new_comment = BlogComment(
            body=form.body.data,
            author_id=current_user.id,
            post_id=post_id
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post", post_id=post_id))
    requested_post = BlogPost.query.get(post_id)
    comments_post = BlogComment.query.filter_by(post_id=post_id).all()
    return render_template("post.html", post=requested_post, form=form, comments=comments_post)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=['GET', 'POST'])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@login_required
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author_id = current_user.id
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
