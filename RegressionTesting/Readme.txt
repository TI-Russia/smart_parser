Run regression tests to determine if changes in parser logic are breaking, i.e. if current parser
output somehow differs from the 'standard'.

Tests are split into two methods – one for Excel files and one for Word files.

To add new file to the regression test battery, place it into the project folder "regression_samples/Word"
or to "regression_samples/Excel", depending on its type. Note that you should add both the source file
and the .json file containing the output you expect to get from it, otherwise test methods will
throw an exception. Newly added files should have their "Copy to Output Directory" property changed to
"Copy always" or "Copy if newer" in order for the test methods to access them.

!!!It might be necessary to clean/rebuild the test project in order for the added files to appear in test output directory.


