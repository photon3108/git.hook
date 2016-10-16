# MIT License
#
# Copyright (c) 2016 Steven Huang <photon3108(at)gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import inspect
import subprocess
import sys

class Node:
    def __init__(self, tree, commit):
        self._tree = tree
        self._commit = commit
        self._parent_list = []

    def parent_list(self):
        if len(self._parent_list) == 0:
            text = git(['cat-file', 'commit', self._commit])

            line_list = text.split('\n')
            for line in line_list:
                token_list = line.split()
                if len(token_list) >= 2 and token_list[0] == 'parent':
                    self._parent_list.append(token_list[1])

        return self._parent_list
    pass

class BranchNode(Node):
    def __init__(self, tree, commit, trunk):
        super().__init__(tree, commit)
        self._trunk = trunk

    def traverse(self):
        if self._commit == self._tree.old_head():
            raise TreeError('Reject old_head(%s) in branch' %(
                self._tree.old_head()[:5]))

        parent_list = self.parent_list()
        log(str(parent_list))

        num_parent = len(parent_list)
        if num_parent != 1:
            raise TreeError('num_parent(%d) at %s in branch' % (
                num_parent, self._commit))

        if parent_list[0] == self._trunk:
            self._tree.set_current_node(TrunkNode(self._tree, parent_list[0]))
            return

        self._tree.set_current_node(
            BranchNode(self._tree, parent_list[0], self._trunk))
        return

class TrunkNode(Node):
    def __init__(self, tree, commit):
        super().__init__(tree, commit)

    def traverse(self):
        if self._commit == self._tree.old_head():
            self._tree.set_current_node(None)
            return

        parent_list = self.parent_list()

        num_parent = len(parent_list)
        if num_parent == 0:
            self._tree.set_current_node(None)
            return
        if num_parent == 1:
            self._tree.set_current_node(TrunkNode(self._tree, parent_list[0]))
            return
        if num_parent != 2:
            raise TreeError('num_parent(%d) at %s' % (num_parent, self._commit))
        if not self._tree.is_master():
            raise TreeError('Only accept fast-forward at non-master branch')

        common_ancestry = git(['merge-base'] + parent_list).rstrip('\n')
        log(str(parent_list))
        log(common_ancestry)
        if common_ancestry not in parent_list:
            raise TreeError('Only accept pure non-fast-forward')

        parent_list.remove(common_ancestry)
        self._tree.set_current_node(
            BranchNode(self._tree, parent_list[0], common_ancestry))

        self._tree.set_current_node(None)
        return

class Tree:
    def __init__(self):
        self.__ref = sys.argv[1]
        self.__old_head = sys.argv[2]
        self.__new_head = sys.argv[3]
        self.__is_master = True
        self.__current_node = None

    def is_master(self):
        return self.__is_master

    def old_head(self):
        return self.__old_head

    def set_current_node(self, node):
        self.__current_node = node

    def traverse(self):
        self.__is_master = False
        if self.__ref.split('/')[-1] == 'master':
            self.__is_master = True

        # Delete branch
        if self.__new_head == '0000000000000000000000000000000000000000':
            log('Delete branch %s' % (self.__old_head))
            return

        # Create branch
        if self.__old_head == '0000000000000000000000000000000000000000':
            log('Creat branch %s' % (self.__new_head))
            return

        try:
            self.__current_node = TrunkNode(self, self.__new_head)
            while self.__current_node != None:
                self.__current_node.traverse()
        except TreeError as e:
            print(e)
            sys.exit(1)
    pass

class TreeError(Exception):
    def __init__(self, value):
        self.__value = value
    def __str__(self):
        return repr(self.__value)

f = sys.stdout

def git(arg_list):
    arg_list = ['git'] + arg_list
    process = subprocess.Popen(arg_list, stdout = subprocess.PIPE)
    buf = process.stdout.read()
    return buf.decode('utf-8')

def log(msg):
    frame_list = inspect.stack()
    frame = frame_list[1]
    f.write("%s, %s():%s:%d\n" % (msg, frame[3], frame[1], frame[2]))

def traverse():
    log("branch(%s), old(%s), new(%s)" % (
        sys.argv[1], sys.argv[2], sys.argv[3]))

    tree = Tree()
    tree.traverse()
    sys.exit(0)

if __name__ == '__main__':
    traverse()
    pass
