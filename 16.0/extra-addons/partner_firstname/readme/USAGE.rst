The field *name* becomes a stored function field concatenating the *last name*
and the *first name*. This avoids breaking compatibility with other modules.

Users should fulfill manually the separate fields for *last name* and *first
name*, but in case you edit just the *name* field in some unexpected module,
there is an inverse function that tries to split that automatically. It assumes
that you write the *name* in format configured (*"Lastname Firstname"*, by default),
but it could lead to wrong splitting (because it's just blindly trying to
guess what you meant), so you better specify it manually.

For the same reason, after installing, previous names for contacts will stay in
the *name* field, and the first time you edit any of them you will be asked to
supply the *last name* and *first name* (just once per contact).
