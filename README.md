Downloading and analysing MAL reviews

The data collection process is done by scraping. Unfortunately, the MAL API does not include reviews, and 3rd party APIs like Jikanpy do not have all the required functionalities, as well as returning inconsistent results compared to what the webpages display.

The data collected include the top 1000 rated anime on MAL as of 27/08/2023 and their top 3 reviews for each tag (Recommended, Mixed Feelings, Not Recommended), and can be replicated by running the `src/extract.py` file.  
Some things are hard coded, but can be easily changed to collect e.g. only movies, top entries by popularity, more than 3 reviews per tag, etc.

The Jupyter notebook shows some example of data processing that was done. The accessory functions it uses are in the `src/process.py` file.
