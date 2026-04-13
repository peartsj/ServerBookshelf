# Schema Notes

Current schema is built for ebook MVP and future audiobook support.

## Core entities

- `users`
- `authors`
- `publishers`
- `series`
- `genres`
- `books`
- `book_genres` (many-to-many)
- `book_files` (supports ebook/audiobook via media type)

## Required metadata covered

- title
- author
- file format
- publisher
- genre
- description
- publishing year
- series
- cover art path
- adaptation status

## Additional fields included for future-proofing

- media type (`ebook` or `audiobook`)
- storage path
- file size
- optional duration (useful for audiobooks)
- optional checksum for file integrity
- optional ISBN-13
- optional language code
- optional series position (book number in series)

## Multi-user ownership

- `books.user_id` assigns each book to a specific user library.
- A book lookup/list operation is scoped to one user.
- `isbn_13` uniqueness is now per user library, not global.

## Adaptation default

- `has_adaptation` defaults to `false` when not provided.
