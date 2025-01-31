import os
import argparse
import pickle
from pathlib import Path
import logging

from agentorg.utils.loader import Loader

logger = logging.getLogger(__name__)


def build_rag(folder_path, docs):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    filepath = os.path.join(folder_path, "documents.pkl")
    loader = Loader()
    crawled_urls = []
    if Path(filepath).exists():
        logger.warning(f"Loading existing documents from {os.path.join(folder_path, 'documents.pkl')}! If you want to recrawl, please delete the file or specify a new --output-dir when initiate Generator.")
        crawled_urls = pickle.load(open(os.path.join(folder_path, "documents.pkl"), "rb"))
    else:
        for doc in docs:
            source = doc.get("source")
            num_docs = doc.get("num") if doc.get("num") else 1
            urls = loader.get_all_urls(source, num_docs)
            crawled_urls.extend(loader.to_crawled_obj(urls))
        Loader.save(filepath, crawled_urls)

    logging.info(f"CRAWLED URLS: {[c.url for c in crawled_urls]}")
    chunked_docs = Loader.chunk(crawled_urls)
    filepath_chunk = os.path.join(folder_path, "chunked_documents.pkl")
    Loader.save(filepath_chunk, chunked_docs)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--base_url", required=True, type=str, help="base url to crawl")
    parser.add_argument("--folder_path", required=True, type=str, help="location to save the documents")
    parser.add_argument("--max_num", type=int, default=10, help="maximum number of urls to crawl")
    args = parser.parse_args()

    build_rag(folder_path=args.folder_path, docs=[{"source": args.base_url, "num": args.max_num}])