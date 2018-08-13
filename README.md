# rss-reader

wip

A simple RSS Reader application which reads xml data adhering to the Atom specification which can be found at <http://www.w3.org/2005/Atom>. Written in Python.

## Features

* Add RSS feeds
* Read their articles
* Automatically fetch new articles
* Unread articles are highlighted
* Sort articles

## Required Packages

Install them with pip.

* PyQt5
* requests
* defusedxml

## Usage

Run by having the required packages and running `rss_reader.py` with python 3. Reset by deleting feeds.db and settings.json.