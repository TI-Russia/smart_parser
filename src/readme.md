===========================
API Validation

It's possible to enable additional validation of JSON output via Declarator API call. To do that:

1. Replace the "username" and "password" lines in the file DeclaratorApiClient/auth.txt with valid username and password.
If you're unsure what those are, contact Alexander Serechenko or Andrew Jvirblis.


2. From your Git shell, run the following command: git update-index --assume-unchanged DeclaratorApiClient/auth.txt

This will tell Git to stop tracking changes to this file in your local repository, so that you don't accidentally commit your login
and password to the Github repo (thus making them public knowledge).


3. Ensure that your Internet connection is working and run smart_parser.exe with the '-api-validation' option.

===========================
Ubuntu install

sudo apt-get install libreoffice
sudo apt-get install -y libgdiplus
