"""Tests for helper utilities."""

from pathlib import Path

import pytest

from wijjit.helpers import load_filesystem_tree


class TestLoadFilesystemTree:
    """Tests for load_filesystem_tree function."""

    def test_load_simple_directory(self, tmp_path):
        """Test loading a simple directory structure.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        # Create test structure
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        # Load tree
        tree = load_filesystem_tree(tmp_path)

        # Verify structure
        assert tree["label"] == tmp_path.name
        assert tree["value"] == str(tmp_path)
        assert tree["type"] == "folder"
        assert "children" in tree
        assert len(tree["children"]) == 3

        # Find children by label
        children_by_label = {child["label"]: child for child in tree["children"]}

        # Verify subdir comes before files (folders first)
        assert tree["children"][0]["label"] == "subdir"

        # Verify files
        assert "file1.txt" in children_by_label
        assert children_by_label["file1.txt"]["type"] == "file"
        assert "size" in children_by_label["file1.txt"]

        # Verify subdirectory
        assert "subdir" in children_by_label
        subdir = children_by_label["subdir"]
        assert subdir["type"] == "folder"
        assert "children" in subdir
        assert len(subdir["children"]) == 1
        assert subdir["children"][0]["label"] == "file3.txt"

    def test_max_depth(self, tmp_path):
        """Test max_depth parameter limits recursion.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        # Create nested structure: root/a/b/c/file.txt
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b").mkdir()
        (tmp_path / "a" / "b" / "c").mkdir()
        (tmp_path / "a" / "b" / "c" / "file.txt").write_text("deep")

        # Load with max_depth=2
        tree = load_filesystem_tree(tmp_path, max_depth=2)

        # Should have: root -> a -> b (depth 2), but not c
        assert "children" in tree
        a_node = tree["children"][0]
        assert a_node["label"] == "a"
        assert "children" in a_node
        b_node = a_node["children"][0]
        assert b_node["label"] == "b"
        # b should not have children (exceeded max_depth)
        assert "children" not in b_node

    def test_show_hidden(self, tmp_path):
        """Test show_hidden parameter.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        # Create files including hidden
        (tmp_path / "visible.txt").write_text("visible")
        (tmp_path / ".hidden").write_text("hidden")
        (tmp_path / ".hiddendir").mkdir()

        # Load without hidden files
        tree = load_filesystem_tree(tmp_path, show_hidden=False)
        labels = [child["label"] for child in tree.get("children", [])]
        assert "visible.txt" in labels
        assert ".hidden" not in labels
        assert ".hiddendir" not in labels

        # Load with hidden files
        tree = load_filesystem_tree(tmp_path, show_hidden=True)
        labels = [child["label"] for child in tree.get("children", [])]
        assert "visible.txt" in labels
        assert ".hidden" in labels
        assert ".hiddendir" in labels

    def test_exclude_patterns(self, tmp_path):
        """Test exclude parameter with glob patterns.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        # Create various files
        (tmp_path / "code.py").write_text("code")
        (tmp_path / "compiled.pyc").write_text("compiled")
        (tmp_path / "data.json").write_text("data")
        (tmp_path / "__pycache__").mkdir()

        # Load with exclusions
        tree = load_filesystem_tree(tmp_path, exclude=["*.pyc", "__pycache__"])

        labels = [child["label"] for child in tree.get("children", [])]
        assert "code.py" in labels
        assert "data.json" in labels
        assert "compiled.pyc" not in labels
        assert "__pycache__" not in labels

    def test_include_files_false(self, tmp_path):
        """Test include_files=False only shows directories.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        # Create mixed structure
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested.txt").write_text("nested")

        # Load directories only
        tree = load_filesystem_tree(tmp_path, include_files=False)

        # Root should only have subdir
        assert len(tree.get("children", [])) == 1
        assert tree["children"][0]["label"] == "subdir"
        assert tree["children"][0]["type"] == "folder"

        # Subdir should have no children (nested.txt excluded)
        assert "children" not in tree["children"][0]

    def test_include_metadata(self, tmp_path):
        """Test include_metadata parameter adds size info.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        # Create file with known content
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")

        # Load with metadata
        tree = load_filesystem_tree(tmp_path, include_metadata=True)
        file_node = tree["children"][0]
        assert "size" in file_node
        assert "B" in file_node["size"] or "KB" in file_node["size"]

        # Load without metadata
        tree = load_filesystem_tree(tmp_path, include_metadata=False)
        file_node = tree["children"][0]
        assert "size" not in file_node

    def test_filter_func(self, tmp_path):
        """Test custom filter function.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        # Create files
        (tmp_path / "keep_this.txt").write_text("keep")
        (tmp_path / "remove_this.txt").write_text("remove")
        (tmp_path / "also_keep.py").write_text("keep")

        # Filter: only keep files with "keep" in name
        def custom_filter(path: Path) -> bool:
            return "keep" in path.name

        tree = load_filesystem_tree(tmp_path, filter_func=custom_filter)

        labels = [child["label"] for child in tree.get("children", [])]
        assert "keep_this.txt" in labels
        assert "also_keep.py" in labels
        assert "remove_this.txt" not in labels

    def test_nonexistent_path(self):
        """Test error handling for nonexistent path."""
        with pytest.raises(FileNotFoundError):
            load_filesystem_tree("/nonexistent/path/xyz123")

    def test_file_instead_of_directory(self, tmp_path):
        """Test error handling when path is a file not directory.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        # Create a file
        test_file = tmp_path / "file.txt"
        test_file.write_text("content")

        # Try to load it as a directory
        with pytest.raises(NotADirectoryError):
            load_filesystem_tree(test_file)

    def test_empty_directory(self, tmp_path):
        """Test loading empty directory.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        tree = load_filesystem_tree(tmp_path)

        assert tree["type"] == "folder"
        # Empty directory should have no children key or empty list
        assert "children" not in tree or tree["children"] == []

    def test_size_formatting(self, tmp_path):
        """Test human-readable size formatting.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        # Create files of different sizes
        (tmp_path / "small.txt").write_text("x" * 100)  # 100 B
        (tmp_path / "medium.txt").write_text("x" * 2000)  # ~2 KB

        tree = load_filesystem_tree(tmp_path, include_metadata=True)
        children_by_label = {child["label"]: child for child in tree["children"]}

        # Check size formats
        small_size = children_by_label["small.txt"]["size"]
        assert "B" in small_size

        medium_size = children_by_label["medium.txt"]["size"]
        assert "KB" in medium_size or "B" in medium_size

    def test_sorted_output(self, tmp_path):
        """Test that output is sorted (folders first, then alphabetically).

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        # Create files and folders in random order
        (tmp_path / "zebra.txt").write_text("z")
        (tmp_path / "apple").mkdir()
        (tmp_path / "banana.txt").write_text("b")
        (tmp_path / "cherry").mkdir()

        tree = load_filesystem_tree(tmp_path)
        labels = [child["label"] for child in tree["children"]]

        # Folders should come first
        assert labels[0] == "apple"
        assert labels[1] == "cherry"
        # Then files alphabetically
        assert labels[2] == "banana.txt"
        assert labels[3] == "zebra.txt"

    def test_string_and_path_input(self, tmp_path):
        """Test that both string and Path inputs work.

        Parameters
        ----------
        tmp_path : Path
            Pytest temporary path fixture
        """
        (tmp_path / "file.txt").write_text("content")

        # Load with string path
        tree1 = load_filesystem_tree(str(tmp_path))
        assert tree1["type"] == "folder"

        # Load with Path object
        tree2 = load_filesystem_tree(tmp_path)
        assert tree2["type"] == "folder"

        # Should produce same result
        assert tree1["label"] == tree2["label"]
        assert tree1["value"] == tree2["value"]
