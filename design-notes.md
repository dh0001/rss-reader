# Design Notes

## Feed Manager

The feed manager manages interactions with the database, and the threads which run background tasks related to the feeds.

Contains a cache which is a list of all the feeds in the program, and is considered the main 'copy' of feeds. Whenever anything is changed in the cache, the database is updated with the same change.

### Database

The database should store persistant data which is accessed often.

It stores feed and article data.  It also stores folder data which organizes the feeds.

## View

The view handles display to the screen.

It manages the qt windows, data models, and interactions with the user.

### Feed Model

The feed model allows the qt window to understand the data provided by the feed manager.

## Settings

The settings stores persistant data which is cached on program start.  It should also be easily accessed using a text editor.

It stores global settings used by the program. 

Since feed data is now always cached, storing feed data there too will be considered.
