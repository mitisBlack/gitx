#!/usr/bin/env python

import argparse
import subprocess
import os

import helpers
from project import Project
import build
from package import package
import sign


def generate_release_notes(project):
    from string import Template

    artifact_signature = helpers.sign_file(project.image_path(), project.update_signing_keyfile())

    attrs = dict()
    attrs['app'] = project.artifact_prefix()
    attrs['version'] = project.build_number()
    attrs['changelog'] = ""
    attrs['signature'] = "" if artifact_signature == None else "Signature: %s" % (artifact_signature)

    template_source = open(project.release_notes_tmpl(), 'r').read()
    release_notes_text = Template(template_source).substitute(attrs)

    with open(project.release_notes_file(), 'w') as release_notes_file:
        release_notes_file.write(release_notes_text)


def tag_release(release_name, force=False):
    tag = ['git', 'tag', release_name]
    if force:
        tag.append('-f')
    subprocess.check_call(tag)
    pass


def publish_release(project, as_draft):
    hub_release = ['hub', 'release',
        'create', project.release_tag_name(),
        '-a', project.image_path(),
        '-m', project.release_name(),
        '-f', project.release_notes_file()]
    if project.label() == "pre":
        hub_release.append('-p')
    if as_draft:
        hub_release.append('-d')

    print("hub: {}".format(hub_release))
    # subprocess.check_call(hub_release)
 

def publish_cmd(args):
    label = None if args.prerelease == False else "pre"
    
    project = Project(os.getcwd(), "release", label)

    print "Preparing release {}".format(project.release_tag_name())
    helpers.assert_clean()
    helpers.assert_branch(project.release_branch())
    helpers.set_version(project.build_version(), project.label())

    print("Building: {}".format(project.build_product()))
    build.build(project)

    print("Signing product with identity \"{}\"".format(project.codesign_identity()))
    sign.sign_everything_in_app(project.build_product(), project.codesign_identity())

    print("Packaging {} to {} as {}".format(project.build_product(), project.image_path(), project.image_name()))
    package(project.build_product(), project.image_path(), project.image_name())

    print("Generating release notes...")
    generate_release_notes(project)

    print("Tagging \"{}\"".format(project.release_tag_name()))
    tag_release(project.release_tag_name())

    print("Publishing {}".format(project.release_name()))
    publish_release(project, args.draft)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--prerelease', action='store_true')
    parser.add_argument('-d', '--draft', action='store_true')
    parser.set_defaults(func=publish_cmd)

    args = parser.parse_args()
    args.func(args)
