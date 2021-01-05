import os
import sys
import zlib
from collections import defaultdict
# importing functions from os for cleaner code 
from os import getcwd, listdir, pardir
from os.path import isfile, isdir, join, abspath

# The below function is used to find the .git directory
def find(name):
	path = getcwd()
	found = name in listdir(path)

	while not found:
		# Before accessing the parent check for root
		if path == "/":
			sys.stdout.write("Not inside a git repository\n")
			exit(1)
		# The cryptic line below just returns the parent directory of path
		path = abspath(join(path, pardir))
		found = name in listdir(path)
	return join(path, name)



class CommitNode:
    def __init__(self, commit_hash):
        """
        :type commit_hash: str
        """
        self.commit_hash = commit_hash
        self.parents = set()
        self.children = set()


# Decmpress file data
def decompress_obj_file(sha_id):
	internal_path = join(sha_id[0:2], sha_id[2:])
	external_path = join(find(".git"), "objects")
	path = abspath(join(external_path, internal_path))
	file = open(path, "rb")
	data = file.read()
	d_data = zlib.decompress(data)
	return d_data.decode("utf-8")

def get_parents(sha_id):
	parent_list = [ line[7:] for line in decompress_obj_file(sha_id).splitlines() if 'parent' in line ]
	return parent_list


# The below function is used to create the list of commit hashes of all the branches that exist
def create_branch_head_list():

    # Private Functions
    def attach_path(prefix, suffix):
        return prefix + "/" + suffix

    def get_data(file):
        file_handle = open(file)
        data = file_handle.read().rstrip()
        return data

    # Get the path where all the branch names exist
    path = abspath(join(find(".git"), "refs/heads"))

    # Seperately store the files and the directories
    # branch_file_list = [get_data(join(path, f)) for f in listdir(path) if isfile(join(path, f))]
    branch_file_dict = defaultdict(list)
    for f in listdir(path):
        if isfile(join(path, f)):
            branch_file_dict[get_data(join(path, f))].append(f)
    branch_dir_list = [d for d in listdir(path) if isdir(join(path, d))]
    
    # Go inside directories until you reach file(s)
    while len(branch_dir_list) != 0:
        # Path to current directory
        t_path = os.path.abspath(os.path.join(path, branch_dir_list[0]))
        # Append all the files in the current directory to branch_files_list
        # branch_file_list.extend([get_data(join(t_path, f)) for f in listdir(t_path) if isfile(join(t_path, f))])
        for f in listdir(t_path):
            if isfile(join(t_path, f)):
                branch_file_dict[get_data(join(t_path, f))].append(join(branch_dir_list[0], f))
        # Append all the directories in current directory to branch_dir_list
        branch_dir_list.extend([attach_path(branch_dir_list[0],d) for d in listdir(t_path) if isdir(join(t_path, d))])
        # Pop the current directory from branch_dir_list
        branch_dir_list.pop(0)

    return branch_file_dict



def build_commit_graph():
	# branch_head list is the list of branch names procured from 
	# .git/refs/heads
	branch_head_list = create_branch_head_list().keys()
	commit_dict = dict()
	# These are the root nodes that don't have any parents
	root_hashes = list()
	# nodes that are visited have their parents updated 
	visited = set()
	# hash stack is the "to be visited" list
	hash_stack = list()
	hash_stack.extend(branch_head_list)
	hash_stack.sort()

	while len(hash_stack) != 0:
		# Get the next element from stack, store it in commit_hash, and remove it from stack
		current_node_hash = hash_stack[0]
		hash_stack.pop(0)

		# if a node is visited then it means that its parents are accounted and so we can 
		# skip to the next entry
		if current_node_hash in visited:
			continue

		# add the node to the visited list 
		visited.add(current_node_hash)

		# if a node is not in commit_dict then it means that it has to be initiated 
		if current_node_hash not in commit_dict:
			commit_dict[current_node_hash] = CommitNode(current_node_hash)
		
		# update the parents 
		parents = set(get_parents(current_node_hash))
		commit_dict[current_node_hash].parents.update(parents)

		# if there are no parents then add the node_hash to list of root_hashes
		if len(commit_dict[current_node_hash].parents) == 0:
			root_hashes.append(current_node_hash)

		# for each parent add the current node in that parent's children list
		for p in commit_dict[current_node_hash].parents:
			# if p is not visited then add it to the "to be visited" list i.e hash_stack
			if p not in visited:
				hash_stack.append(p)
			# if p is not in the commit dict then initiate it 
			if p not in commit_dict:
				commit_dict[p] = CommitNode(p)
			# update the children of p by adding current node 
			commit_dict[p].children.add(current_node_hash)
	return commit_dict, root_hashes


def get_topo_ordered_vertices():
	# Get the commit graph
	commit_dict, root_hashes = build_commit_graph()
	order = list()
	visited = set()
	temp_stack = list()
	hash_stack = sorted(root_hashes)

	while len(hash_stack) != 0:
		current_hash = hash_stack.pop()
		# if the current hash is visited move on to the next
		if current_hash in  visited:
			continue
		visited.add(current_hash)

		# if the top of the stack is not the immideate parent of current hash then 
		# it means that there is a jump and so temp_stack must be pushed into order
		while len(temp_stack) != 0 and temp_stack[-1] not in commit_dict[current_hash].parents:
			temp = temp_stack.pop()
			order.append(temp)

		# append current hash to temp_stack
		temp_stack.append(current_hash)

		# append all the children of current hash to the stack 
		for c in sorted(commit_dict[current_hash].children):
			if c not in visited:
				hash_stack.append(c)

	# transfer the rest of temp_stack to order
	while len(temp_stack) != 0:
		order.append(temp_stack.pop())

	return order


# function directly taken from assignment hints
def print_topo_ordered_commits_with_branch_names(commit_nodes, topo_ordered_commits, head_to_branches): 
	jumped = False
	for i in range(len(topo_ordered_commits)):
		commit_hash = topo_ordered_commits[i]
		
		if jumped:
			jumped = False
			sticky_hash = ' '.join(sorted(commit_nodes[commit_hash].children))
			print(f'={sticky_hash}')
		
		branches = sorted(head_to_branches[commit_hash]) if commit_hash in head_to_branches else [] 
		print(commit_hash + (' ' + ' '.join(branches) if branches else ''))
		
		if i+1 < len(topo_ordered_commits) and topo_ordered_commits[i+1] not in commit_nodes[commit_hash].parents: 
			jumped = True
			sticky_hash = ' '.join(sorted(commit_nodes[commit_hash].parents))
			print(f'{sticky_hash}=\n')

print_topo_ordered_commits_with_branch_names(build_commit_graph()[0], get_topo_ordered_vertices(), create_branch_head_list())


