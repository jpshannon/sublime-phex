import sublime
import sublime_plugin
import os
import re
import json

VIEW_NAME = "Phex"

class Pref:
    @staticmethod
    def load():
        settings = sublime.load_settings('phex.sublime-settings')

        Pref.default_author    = settings.get('phex_default_author')
        Pref.default_copyright = settings.get('phex_default_copyright')
        Pref.default_license   = settings.get('phex_default_license')
        Pref.default_source_dir = settings.get('phex_default_source_dir')

def plugin_loaded():
    Pref.load()

class PhexBase(sublime_plugin.WindowCommand):
    def display_results(self):
        display = ShowInPanel(self.window)
        display.display_results()

    def window(self):
        return self.view.window()

class PhexInputBase(PhexBase):
    def run(self):
        self.input_panel_view = self.window.show_input_panel(
            self.INPUT_PANEL_CAPTION,
            "",
            self.on_done,
            self.on_update,
            self.on_cancel
        )

        self.input_panel_view.set_name(VIEW_NAME)
        self.input_panel_view.settings().set("auto_complete_commit_on_tab", False)
        self.input_panel_view.settings().set("tab_completion", False)
        self.input_panel_view.settings().set("translate_tabs_to_spaces", False)
        self.input_panel_view.settings().set("anf_panel", True)
        self.view = self.window.active_view()

def getNamespaceAutocompletion(input):
    if not input.endswith("\t"):
        return None

    input = input.replace("\t", "")

    input_dirs = ""
    if not input.find("\\") == -1:
        input_dirs = input.split("\\")
        input_dirs = os.sep+os.sep.join(input_dirs[:-1])

    input_namespace = ""
    if len(input_dirs):
        input_namespace = input_dirs.replace(os.sep, "\\")+"\\"

    matches = []

    source_root = getSourceRoot(getProjectRoot())

    min_length = None
    for dirname in os.listdir(source_root+input_dirs):
        if os.path.isdir(source_root+input_dirs+os.sep+dirname):
            namespace = dirname.replace(source_root, "")
            namespace = input_namespace+namespace.replace(os.sep, "\\")
            if namespace.startswith("\\"):
                namespace = namespace[1:]
            if re.match(input.replace("\\", ";"), namespace.replace("\\", ";"), re.I):
                matches.append(namespace)
                if min_length is None or len(namespace) < min_length:
                    min_length = len(namespace)

    if len(matches) == 1:
        return matches[0]

    best_match = ""
    for i in range(0, min_length):
        letter = None
        for match in matches:
            if letter is None:
                letter = match[i]
            elif letter == match[i]:
                best_match += match[i]

    return best_match


"""
    Returns the @author PHPDoc
"""
def getAuthorPhpDoc(input):
    author = ""
    if Pref.default_author:
        author = " * @author    "+Pref.default_author+"\n"

    return author

"""
    Returns the @copyright PHPDoc
"""
def getCopyrightPhpDoc(input):
    copyright = ""
    if Pref.default_copyright:
        copyright = " * @copyright "+Pref.default_copyright+"\n"

    return copyright

"""
    Returns the @license PHPDoc
"""
def getLicensePhpDoc(input):
    license = ""
    if Pref.default_license:
        license = " * @license   "+Pref.default_license+"\n"

    return license

"""
    Returns the index of the character where the class name starts
"""
def getClassNameStart(input):
    class_name_start = input.rfind("\\")
    if class_name_start == -1:
        class_name_start = 0

    return class_name_start

"""
    Returns the class name of the given input.

    Mostly what this method does is removing the namespace.
"""
def getClassName(input):
    class_name_start = getClassNameStart(input)

    if input[(class_name_start)] == "\\":
        return input[(class_name_start+1):]
    else:
        return input[class_name_start:]

"""
    Returns the interface name of the given input.
"""
def getInterfaceName(input):
    return getClassName(input)+"Interface"

"""
    Returns the namespace from the given input.

    The returned string includes the namespace statement.
"""
def getNamespace(namespace_name):
    namespace = ""
    if len(namespace_name) > 0:
        namespace = "namespace "+namespace_name+";\n\n"

    return namespace

def getNamespaceName(input, relative = False):
    class_name_start = getClassNameStart(input)

    namespace_name = input[:class_name_start]

    if relative:
        prefix = getWorkingDirectory().replace(getSourceRoot(getProjectRoot())+os.sep, "")
        if len(prefix) > 0:
            if len(namespace_name) > 0:
                prefix += "\\"
            namespace_name = prefix+namespace_name

    return namespace_name.replace(os.sep, "\\")

"""
    Returns the filename for the given input.
    The input is most likely a class name (with our without namespace).
    However, it can also be prefixed with ~

    If the input is prefixed with `~` return the path based on the currently active view, otherwise return the path
    based from the guessted base directory.
"""
def getFilenameFromInput(input, namespace, relative = False, interface = False):
    if relative:
        path = getWorkingDirectory()
    else:
        path = getSourceRoot(getProjectRoot())
        psr4Namespaces = getComposerPsr4Namespaces()
        for (ns, nspath) in psr4Namespaces.items():
            ns = re.sub("\\$", "", ns)
            namespace += "\\"
            if namespace.find(ns) == 0:
                input = input.replace(ns, "")

    interface_part = ""
    if interface:
        interface_part = "Interface"

    return path+os.sep+input.replace("\\", os.sep)+interface_part+".php"

"""
    Creates the given file (and the directory if necessary) and writes the content to it.
    It also sets the syntax highlighting to PHP
"""
def createPhpFile(file, contents):
    if contents is None:
        return
    if not os.path.exists(os.path.dirname(file)):
        os.makedirs(os.path.dirname(file))
    open(file, "w")
    view = sublime.active_window().open_file(file)
    view.set_syntax_file("Packages"+os.sep+"php-extended"+os.sep+"PHP.tmLanguage")
    sublime.set_timeout(lambda: insertAndSave(view, contents), 100)

"""
    Inserts the content in the view and saves the view.
"""
def insertAndSave(view, contents):
    view.run_command("insert_snippet", {"contents": contents})
    view.run_command("save")
