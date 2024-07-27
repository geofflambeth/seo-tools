import quick_seo_audit_tools.functions.database as db
from datetime import datetime
from flask import Flask
from flask import request
from flask import render_template



app = Flask(__name__)
db_path = f'../test_folder/2024-07-11_crawl-database.db' # REMEMBER TO CHANGE LATER
db.init_output_db(db_path)

@app.route("/")
def hello_world():
    network_analysis_data = db.list_network_analysis_values()
    list = ''.join([f"<li><a href='/inspect-url?url={i}'>{i}</a></li>" for i in db.list_distinct_requests()])
    return f'<ul>{list}</ul>'

@app.route("/inspect-url")
def inspect_url():
    list = [i for i in db.list_distinct_requests()]
    url_to_inspect = request.args.get('url', '')
    if url_to_inspect and url_to_inspect in list:
        return render_template('inspect-url.html',
                               page_data=db.show_page_data(url_to_inspect),
                               in_links=db.return_ranked_in_links(url_to_inspect),
                               canonicalized_urls=db.return_canonicalized_urls(url_to_inspect)
        )
    elif url_to_inspect == "":
        return "<p>No url was provided.</p>"
    else:
        return "<p>This url does not exist</p>"