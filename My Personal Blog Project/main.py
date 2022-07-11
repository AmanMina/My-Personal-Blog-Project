import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from flask_ckeditor import CKEditor, CKEditorField
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from flask_gravatar import Gravatar
from werkzeug.security import generate_password_hash, check_password_hash



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///user-blogs-data.db"
app.config['SECRET_KEY'] = '123456'
ckeditor = CKEditor(app)
db = SQLAlchemy(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)










##CONFIGURE TABLE
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    comment_author = relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)




# db.create_all()




class NewBlogForm(FlaskForm):
    title = StringField(label='Blog Post Title')
    subtitle = StringField(label='Subtitle')
    body = CKEditorField(label='Body')
    submit = SubmitField(label='Add Blog')


class NewUserForm(FlaskForm):
    name = StringField(label='Your Name')
    email = StringField(label='Your Email')
    password = StringField(label='Your New Password')
    submit = SubmitField(label='Register')


class LoginForm(FlaskForm):
    email = StringField(label='Your Email')
    password = StringField(label='Your New Password')
    submit = SubmitField(label='Log In')


class CommentForm(FlaskForm):
    comment_text = StringField(label='Comment')
    submit = SubmitField(label='Comment')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def homepage():
    blogs_data = db.session.query(BlogPost).all()
    return render_template("index.html", blogs=blogs_data, current_user=current_user)


@app.route('/about')
def about():
    return render_template("about.html", current_user=current_user)


@app.route('/contact', methods=['POST', 'GET'])
def contact_page():
    if request.method == 'POST':
        print(request.form['name'])
        return render_template("contact.html", heading="Submitted", current_user=current_user)
    elif request.method == 'GET':
        return render_template("contact.html", heading="Contact Me", current_user=current_user)


@app.route('/post/<int:post_id>', methods=['POST', 'GET'])
def post(post_id):
    requested_post = None
    blogs_data = db.session.query(BlogPost).all()
    for blog_post in blogs_data:
        if blog_post.id == post_id:
            requested_post = blog_post
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        new_comment = Comment(
            text=comment_form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post,
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('post', post_id=requested_post.id))
    return render_template("post.html", post=requested_post, current_user=current_user, form=comment_form)


@app.route('/new-post', methods=['POST', 'GET'])
@login_required
def new_post():
    new_blog_form = NewBlogForm()
    if new_blog_form.validate_on_submit():
        new_blog = BlogPost(
            title=new_blog_form.title.data,
            subtitle=new_blog_form.subtitle.data,
            author=current_user,
            body=new_blog_form.body.data,
            date=datetime.datetime.now().date(),
        )
        db.session.add(new_blog)
        db.session.commit()
        return redirect(url_for('homepage'))


    return render_template('makepost.html', form=new_blog_form, current_user=current_user)



@app.route('/edit-post/<int:id>', methods=['POST', 'GET'])
@login_required
def edit_post(id):
    blog_to_edit = BlogPost.query.get(id)
    new_blog_form = NewBlogForm(
        title=blog_to_edit.title,
        subtitle=blog_to_edit.subtitle,
        body=blog_to_edit.body
    )
    if new_blog_form.validate_on_submit():
        blog_to_edit.title = new_blog_form.title.data
        blog_to_edit.subtitle = new_blog_form.subtitle.data
        blog_to_edit.body = new_blog_form.body.data
        db.session.commit()
        return redirect(url_for('homepage'))
    return render_template('makepost.html', form=new_blog_form, is_edit=True, current_user=current_user)


@app.route('/delete/<int:id>')
@login_required
def delete_post(id):
    post_to_delete = BlogPost.query.get(id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('homepage'))


@app.route('/register', methods=['POST', 'GET'])
def register():
    new_user_form = NewUserForm()
    if new_user_form.validate_on_submit():
        if User.query.filter_by(email=new_user_form.email.data).first():
            flash("User already exist. Log In")
            return redirect(url_for('login'))
        else:
            hashed_password = generate_password_hash(
                new_user_form.password.data,
                method="pbkdf2:sha256",
                salt_length=8
            )
            new_user = User(
                name=new_user_form.name.data,
                email=new_user_form.email.data,
                password=hashed_password,
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('homepage'))
    return render_template('register.html', form=new_user_form, current_user=current_user)


@app.route('/login', methods=['POST', 'GET'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        email = login_form.email.data
        password = login_form.password.data
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('homepage'))
            else:
                flash("Incorrect password")
                return redirect(url_for('login'))
        else:
            flash("User not found")
            return redirect(url_for('login'))
    return render_template('login.html', form=login_form, current_user=current_user)


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    logout_user()
    return redirect(url_for('homepage'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
