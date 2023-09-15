from flask import Flask,render_template
import requests
from datetime import datetime as dt
app=Flask(__name__)

resposta=requests.get('https://api.npoint.io/911d19d520d28bb02cd5')
data=resposta.json()

@app.route('/')
def home():
    return render_template('index.html',posts=data)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/post/<id>')
def post(id):
    return render_template('post.html',id=int(id)-1,post_clickado=data)

if __name__== "__main__":
    app.run(debug=True)