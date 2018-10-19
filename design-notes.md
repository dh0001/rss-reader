# Design Notes

## FeedManager

The feed manager should manage interactions with the database.  View should use the interface provided by it to get data.

Feed data is stored in memory, and saved on disk when changed and on program exit.  Article data is stored in an sqlite database.


## View

The view handles display to the screen.

It manages the qt windows, data models, and interactions with the user.


## Settings

The settings stores persistant data. The data is cached on program start, and saved on change and program end.
