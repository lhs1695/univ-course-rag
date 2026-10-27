export function folderOptions(folders) {
  const options = [];
  for (const root of folders.filter(folder => !folder.parent_id)) {
    options.push({ ...root, label: root.name });
    for (const child of folders.filter(folder => folder.parent_id === root.id)) {
      options.push({ ...child, label: `${root.name} / ${child.name}` });
    }
  }
  return options;
}

export function documentGroups(documents, folders) {
  const groups = folderOptions(folders).map(folder => ({
    ...folder, documents: [],
  }));
  // The library landing view includes every course document, including root files.
  groups.push({ id: null, label: '全部资料', documents: [...documents] });
  const byId = new Map(groups.map(group => [group.id, group]));
  for (const document of documents) {
    const id = document.folder_id ?? null;
    if (id === null) continue;
    if (!byId.has(id)) {
      const group = { id, label: document.folder_name || '资料夹', documents: [] };
      groups.push(group);
      byId.set(id, group);
    }
    byId.get(id).documents.push(document);
  }
  return groups;
}

export function libraryGroup(documents, folders, folderId, search = '') {
  const query = search.trim().toLocaleLowerCase();
  if (query) {
    return {
      id: null, label: '搜索结果',
      documents: documents.filter(document => document.filename.toLocaleLowerCase().includes(query)),
    };
  }
  const groups = documentGroups(documents, folders);
  return groups.find(group => group.id === folderId) || groups.find(group => group.id === null);
}

// Folder counts are direct contents; the landing entry counts the whole course.
export function folderTree(groups) {
  const node = group => ({
    ...group, key: group.id ?? 'all', value: group.id ?? '',
    label: group.name || group.label, count: group.documents?.length ?? 0,
  });
  const all = groups.find(group => group.id === null);
  return [
    ...(all ? [node(all)] : []),
    ...groups.filter(group => group.id !== null && !group.parent_id).map(root => ({
      ...node(root), children: groups.filter(group => group.parent_id === root.id).map(node),
    })),
  ];
}

// Moving a file to the root is different from browsing all course files.
export function documentFolderTargets(folders) {
  return folderTree(documentGroups([], folders)).map(node => (
    node.id === null ? { ...node, label: '课程根目录' } : node
  ));
}

export function folderParentOptions(folders, folder = null) {
  if (folder && folders.some(candidate => candidate.parent_id === folder.id)) return [];
  return folders.filter(candidate => !candidate.parent_id && candidate.id !== folder?.id);
}
