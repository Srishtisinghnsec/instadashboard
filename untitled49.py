# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from instagrapi import Client
from datetime import datetime
import pandas as pd
import os
import matplotlib.pyplot as plt

app = FastAPI()

# Function to log in and fetch insights
def fetch_instagram_insights(username, password):
    cl = Client()
    try:
        # Login to Instagram
        cl.login(username, password)
        print("Login successful!")


        # Fetch the user's account
        user_id = cl.user_id_from_username(username)
        print(f"User ID for {username}: {user_id}")
        user_info = cl.user_info(user_id)

        insights_data = []
        summary_data_list = []  # List to hold summary data

        total_likes = 0
        total_comments = 0
        total_view_counts = 0
        total_content = 0

        # Store the previous month for comparison
        previous_month = None

        # Fetch user's recent media (posts)
        medias = cl.user_medias(user_id)  # Fetch all posts

        for media in reversed(medias):  # Start from the most recent
            media_info = cl.media_info(media.id)

            # Extract the month and year from the media's created time
            media_month = media_info.taken_at.month
            media_year = media_info.taken_at.year

            if previous_month is None:
                previous_month = (media_month, media_year)  # Initialize the first month
            elif (media_month, media_year) != previous_month:
                # Save the summary for the previous month
                summary_data = {
                    "Total Likes": total_likes,
                    "Total Comments": total_comments,
                    "Total Views": total_view_counts,
                    "Total Content": total_content,
                    "Engagement Rate": ((total_likes + total_comments) / (user_info.follower_count * total_content) * 100) if total_content > 0 else 0,
                    "Followers": user_info.follower_count,
                    "Following": user_info.following_count,
                    "Month": datetime(previous_month[1], previous_month[0], 1).strftime("%B"),
                    "Year": previous_month[1]
                }
                summary_data_list.append(summary_data)  # Add to the list of summaries

                # Reset totals for the new month
                total_likes = 0
                total_comments = 0
                total_view_counts = 0
                total_content = 0
                previous_month = (media_month, media_year)  # Update to the new month

            # Process media information
            insights_data.append({
                "media_id": media.id,
                "likes": media_info.like_count,
                "comments": media_info.comment_count,
                "caption": media_info.caption_text,
                "created_time": media_info.taken_at,
                "no_of_views": media_info.view_count,
            })

            # Update total counts
            total_likes += media_info.like_count
            total_comments += media_info.comment_count
            total_view_counts += media_info.view_count or 0
            total_content += 1

        # Add the final summary for the last month
        summary_data = {
            "Total Likes": total_likes,
            "Total Comments": total_comments,
            "Total Views": total_view_counts,
            "Total Content": total_content,
            "Engagement Rate": ((total_likes + total_comments) / (user_info.follower_count * total_content) * 100) if total_content > 0 else 0,
            "Followers": user_info.follower_count,
            "Following": user_info.following_count,
            "Month": datetime(previous_month[1], previous_month[0], 1).strftime("%B"),
            "Year": previous_month[1]
        }
        summary_data_list.append(summary_data)  # Add the last month's summary to the list

        # Create a DataFrame from the summary data list
        summary_df = pd.DataFrame(summary_data_list)
        summary_file_name = f"{username}_insta_summary.csv"

        # Check if the file already exists
        if os.path.exists(summary_file_name):
            existing_summary_df = pd.read_csv(summary_file_name)
            for index, row in summary_df.iterrows():
                month_year = (row["Month"], row["Year"])
                existing_row = existing_summary_df[
                    (existing_summary_df["Month"] == row["Month"]) &
                    (existing_summary_df["Year"] == row["Year"])
                ]

                if existing_row.empty:
                    existing_summary_df = existing_summary_df.append(row, ignore_index=True)
                else:
                    existing_row = existing_row.iloc[0]
                    if (existing_row["Total Likes"] != row["Total Likes"] or
                        existing_row["Total Comments"] != row["Total Comments"] or
                        existing_row["Total Views"] != row["Total Views"] or
                        existing_row["Total Content"] != row["Total Content"] or
                        existing_row["Engagement Rate"] != row["Engagement Rate"]):
                        existing_summary_df.loc[
                            existing_summary_df.index[
                                (existing_summary_df["Month"] == row["Month"]) &
                                (existing_summary_df["Year"] == row["Year"])
                            ][0]
                        ] = row
        else:
            existing_summary_df = summary_df

        # Sort combined summary by Year and Month (Latest first)
        existing_summary_df['YearMonth'] = existing_summary_df['Year'].astype(str) + '-' + existing_summary_df['Month']
        existing_summary_df['YearMonth'] = pd.to_datetime(existing_summary_df['YearMonth'])
        existing_summary_df = existing_summary_df.sort_values(by='YearMonth', ascending=False).drop(columns=['YearMonth'])

        existing_summary_df.to_csv(summary_file_name, index=False)

        print(f"Summary data saved to {summary_file_name}")
        return summary_file_name  # Return the file name for download or further processing

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# FastAPI route to fetch insights
@app.post("/fetch_insights/")
async def fetch_insights(username: str, password: str):
    summary_file_name = fetch_instagram_insights(username, password)
    return {"message": "Insights fetched successfully", "summary_file": summary_file_name}

# FastAPI route to plot the insights (optional)
@app.get("/plot/")
async def plot_insights(filename: str):
    plot(filename)
    return {"message": "Plot generated successfully"}

# Plotting function (unchanged)
def plot(filename):
    summary_df = pd.read_csv(filename)

    # Combine Month and Year for x-axis
    summary_df['Month_Year'] = summary_df['Month'] + ' ' + summary_df['Year'].astype(str)

    # Bar graph for Likes, Comments, and Views
    plt.figure(figsize=(12, 6))

    # Bar plot for Likes, Comments, and Views
    plt.subplot(1, 2, 1)  # 1 row, 2 columns, 1st subplot
    bar_width = 0.25
    x = range(len(summary_df))

    plt.bar(x, summary_df['Total Likes'], width=bar_width, label='Likes', align='center')
    plt.bar([p + bar_width for p in x], summary_df['Total Comments'], width=bar_width, label='Comments', align='center')
    plt.bar([p + bar_width * 2 for p in x], summary_df['Total Views'], width=bar_width, label='Views', align='center')

    plt.xlabel('Month and Year')
    plt.ylabel('Counts')
    plt.title('Likes, Comments, and Views')
    plt.xticks([p + bar_width for p in x], summary_df['Month_Year'], rotation=45)
    plt.legend()
    plt.grid(axis='y')

    # Line graph for Followers, Following, and Engagement Rate
    plt.subplot(1, 2, 2)  # 1 row, 2 columns, 2nd subplot

    plt.plot(summary_df['Month_Year'], summary_df['Followers'], marker='o', label='Followers')
    plt.plot(summary_df['Month_Year'], summary_df['Following'], marker='o', label='Following')
    plt.plot(summary_df['Month_Year'], summary_df['Engagement Rate'], marker='o', label='Engagement Rate')

    plt.xlabel('Month and Year')
    plt.ylabel('Counts / Rate')
    plt.title('Followers, Following, and Engagement Rate')
    plt.xticks(rotation=45)
    plt.legend()
    plt.grid()

    # Adjust the layout and show plots
    plt.tight_layout()
    plt.show()

# To run the FastAPI app
# Use this command in the terminal: uvicorn your_script_name:app --reload
username=input("enter username")
password=input("enter password")
fetch_instagram_insights(username,password)
