#! /bin/bash
# Uses imagemagick to add drop shadows to the screenshots, which makes them
# look nice on white backgrounds.
#
# https://dev.to/corentinbettiol/how-to-make-super-duper-shadows-for-your-screenshots-2m17
# https://stackoverflow.com/a/60681983
# https://stackoverflow.com/a/20796617
for filename in res/screenshots/*.png; do
    echo "$filename"
    convert "$filename" \( +clone -background black -shadow 75x10+0+0 \) +swap -bordercolor none -background none -border 5 -layers merge +repage "$filename"
done
