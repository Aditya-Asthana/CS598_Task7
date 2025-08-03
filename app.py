from flask import Flask, render_template, request
import json
import pandas as pd
from collections import defaultdict
import gzip
import json



app = Flask(__name__)

with open("business.json") as f:
    business_data = [json.loads(line) for line in f]

business_df = pd.DataFrame(business_data)
business_df = business_df[business_df['categories'].apply(lambda x: isinstance(x, list) and "Restaurants" in x)]
business_df = business_df[["business_id", "name", "categories", "city", "stars", "review_count", "full_address"]]

with open("review1.json") as f:
    review_data = [json.loads(line) for line in f]

review_df = pd.DataFrame(review_data)
review_df = review_df[["business_id", "stars", "text"]]

unique_cities = sorted(business_df["city"].dropna().unique())
unique_cuisines = sorted({
    cat.strip()
    for cats in business_df["categories"].dropna()
    for cat in cats if cat != "Restaurants"
})


def get_ranked_restaurants(city, cuisine, top_n=10):
    city_df = business_df[business_df["city"].str.lower() == city.lower()]

    city_df = city_df[
        city_df["categories"].apply(
            lambda cats: any(
                cuisine.lower() in c.lower() for c in cats if c != "Restaurants"
            )
        )
    ]

    if city_df.empty:
        return []

    merged = pd.merge(city_df, review_df, on="business_id")

    grouped = merged.groupby(["business_id", "name", "full_address"]).agg({
        "stars_x": "first",        
        "review_count": "first",  
        "stars_y": "mean"         
    }).reset_index()

    grouped = grouped.rename(columns={
        "stars_x": "business_rating",
        "stars_y": "average_review_rating"
    })

    ranked = grouped.sort_values(by=["review_count", "average_review_rating"], ascending=False)

    return ranked.head(top_n).to_dict(orient="records")



@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        city = request.form["city"]
        cuisine = request.form["cuisine"]
        results = get_ranked_restaurants(city, cuisine)
        return render_template("results.html", city=city, cuisine=cuisine, results=results)
    else:
        return render_template("index.html", cities=unique_cities, cuisines=unique_cuisines)


if __name__ == "__main__":
    app.run(debug=True)
