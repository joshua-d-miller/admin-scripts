#!/usr/local/bin/psupython
# pylint:disable=C0103, C0111, E1101, W0612, W0703, W0612
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Runs AutoPKG
  - Parses the results
  - Outputs the parsed results to Microsoft Teams as follows:
    AutoPKG Run - Time of AutoPKG Run
      Repo Updates:
      Recipe Trusts:
      Software Updates:
      Error Recipes:
      Deprecated Recipes:

-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: June 16, 2020
  Tested: Python 3.8.0

-------------------------------------
'''

# Imports
from __future__ import print_function
import datetime
import json
import os
import plistlib
import subprocess
import tempfile

# --------------------------------------------------------
def build_bulleted_list(leading_text, output_list):
    '''Builds a bulleted list of our parsed output'''
    constructed_list = "{0:}  \n{1:}".format(
        leading_text, "  \n".join(str(
            "&nbsp;&nbsp;&nbsp;&nbsp;&#8226; " + list_item)
                                  for list_item in output_list))
    return constructed_list

# --------------------------------------------------------
def build_recipe_list(dir_to_search):
    '''Builds a list of recipes to verify and run by
    what is in the defined RecipeOverrides directory'''
    built_recipe_list = sorted(os.listdir(dir_to_search))

    return built_recipe_list

# --------------------------------------------------------
def update_autopkg_repos():
    '''Update the recipe repos for AutoPKG'''
    repos = subprocess.check_output(
        ['/usr/local/bin/autopkg', 'repo-list'],
        stderr=subprocess.PIPE).splitlines()

    updated_repos = []

    # Update Recipe Repos
    for repo in repos:
        if repo == '':
            continue
        repo = repo.decode('ascii')
        repo_index = repo.find('https')
        repo = repo[repo_index:-1]
        repo_output = subprocess.check_output(
            ['/usr/local/bin/autopkg', 'repo-update',
             repo], stderr=subprocess.PIPE).decode('ascii')
        if 'Already up to date.' in repo_output:
            continue
        else:
            updated_repos.append(repo.replace(
                'https://github.com/autopkg/', ''))

    if updated_repos:
        repo_update_text = build_bulleted_list(
            'The following repos were updated:', updated_repos)
    else:
        repo_update_text = 'No repos required update'


    return repo_update_text

# --------------------------------------------------------
def verify_autopkg_trusts(recipes):
    '''Verifies the trusts we currently have then reports
    any that need updated to Teams'''

    trusts_to_update = []

    # Update Trusts
    for recipe in recipes:
        try:
            subprocess.check_output(
                ['/usr/local/bin/autopkg', 'verify-trust-info',
                 recipe.replace('.recipe', '')],
                stderr=subprocess.PIPE)
        except Exception:
            trusts_to_update.append(
                recipe.replace('.recipe', ''))
            continue
    # Build the bulleted list if needed
    if trusts_to_update:
        trusts_update_text = build_bulleted_list(
            'These recipes require verificaiton:', trusts_to_update)
    else:
        trusts_update_text = 'No recipes require verification'

    return trusts_update_text

# --------------------------------------------------------
def autopkg_run(recipes, temp_directory):
    '''Runs autopkg and reports the results to Teams'''

    munki_imported_recipes = []
    error_recipes = []
    deprecated_recipes = []

    for recipe in recipes:
        temp_recipe_directory = tempfile.mkdtemp()
        temp_plist = (temp_directory + "/{0:}").format(
            recipe.replace('.recipe', ''))
        if os.path.isfile(temp_plist):
            os.remove(temp_plist)
        try:
            # Run the recipe
            subprocess.check_call(
                ['/usr/local/bin/autopkg', 'run',
                 recipe.replace('.recipe', ''),
                 '--report-plist',
                 temp_plist], stderr=subprocess.PIPE)
        except Exception as error:
            print(error)
            # Capture the error if needed
            error_recipes.append(recipe.replace(
                '.munki.recipe', ''))
            continue
        with open(temp_plist, 'rb') as tmp_plist:
            item_summary = plistlib.load(tmp_plist)
        # Capture the imported or deprecated item's name
        # if an import was done or deprecation is present
        if item_summary['summary_results']:
            if ('deprecation_summary_result' in
                    item_summary['summary_results']):
                deprecated_recipes.append(recipe.replace(
                    '.munki.recipe', ''))
                os.remove(temp_plist)
                continue
            if ('munki_importer_summary_result' in
                    item_summary['summary_results']):
                name = str(item_summary['summary_results'][
                    'munki_importer_summary_result'][
                        'data_rows'][0]['name'])
                version = str(item_summary['summary_results'][
                    'munki_importer_summary_result'][
                        'data_rows'][0]['version'])
                munki_imported_recipes.append('{0:} - {1:}'.format(
                    name, version))
        os.remove(temp_plist)

    if munki_imported_recipes:
        software_updated_text = build_bulleted_list(
            'The following items were downloaded and imported'
            ' into the munki repository:', munki_imported_recipes)
    else:
        software_updated_text = (
            'No items were imported in the the munki repository'
        )

    if error_recipes[0] != '':
        error_recipe_text = build_bulleted_list(
            'The following recipes encountered an error:', error_recipes)
    else:
        error_recipe_text = (
            "No recipes encountered an error."
        )

    if deprecated_recipes:
        deprecated_recipe_text = build_bulleted_list(
            'The following recipes are deprecated and should be '
            'removed:', deprecated_recipes)
    else:
        deprecated_recipe_text = (
            'No recipes are currently deprecated.'
        )

    return software_updated_text, error_recipe_text, deprecated_recipe_text

# --------------------------------------------------------
def main():
    '''Main function'''
    # Create Temporary Working Directory
    temp_directory = tempfile.mkdtemp()
    # Teams WebHook address and Override Directory
    teams_webhook = ('Your Teams WebHook Here')
    override_dir = 'Location Of your Override Directory'

    # Build out recipe list
    recipe_list = build_recipe_list(override_dir)
    # Get current date and time
    autopkg_start_time = (
        datetime.datetime.now().strftime('%B %d, %Y %I:%M %p'))
    # Update Repos
    repo_update_text = update_autopkg_repos()
    # Verify Trusts
    trusts_update_text = verify_autopkg_trusts(recipe_list)
    # Run AutoPKG Recipes
    software_imported, error_software, deprecated_software = autopkg_run(
        recipe_list, temp_directory)

    # Build Teams Notification for AutoPKG
    autopkg_full_teams_notification = {
        'text': '**Repo Updates:** {0:}  \n'
                '**Recipe Trusts:** {1:}  \n'
                '**Software Updates:** {2:}  \n'
                '**Error Recipes:** {3:}  \n'
                '**Deprecated Recipes:** {4:}'.format(
                    repo_update_text, trusts_update_text,
                    software_imported, error_software,
                    deprecated_software),
        'textformat': 'markdown',
        'title': 'AutoPKG Run - {0:}'.format(autopkg_start_time)
    }

    # Send AutoPKG Teams Notification
    subprocess.check_output(
        ['/usr/bin/curl', '-H', 'Content-Type: application/json',
         '-d', json.dumps(autopkg_full_teams_notification), teams_webhook],
        stderr=subprocess.PIPE
    )

if __name__ == '__main__':
    main()
