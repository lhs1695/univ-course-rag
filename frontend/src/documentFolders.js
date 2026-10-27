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
  groups.push({ id: null, label: '未分组', documents: [] });
  const byId = new Map(groups.map(group => [group.id, group]));
  for (const document of documents) {
    const id = document.folder_id ?? null;
    if (!byId.has(id)) {
      const group = { id, label: document.folder_name || '资料夹', documents: [] };
      groups.push(group);
      byId.set(id, group);
    }
    byId.get(id).documents.push(document);
  }
  return groups;
}

// Counts are direct contents: selecting a root never silently includes its children.
export function folderTree(groups) {
  const node = group => ({
    ...group, key: group.id ?? 'ungrouped', value: group.id ?? '',
    label: group.name || group.label, count: group.documents?.length ?? 0,
  });
  const ungrouped = groups.find(group => group.id === null);
  return [
    ...(ungrouped ? [node(ungrouped)] : []),
    ...groups.filter(group => group.id !== null && !group.parent_id).map(root => ({
      ...node(root), children: groups.filter(group => group.parent_id === root.id).map(node),
    })),
  ];
}

export function folderParentOptions(folders, folder = null) {
  if (folder && folders.some(candidate => candidate.parent_id === folder.id)) return [];
  return folders.filter(candidate => !candidate.parent_id && candidate.id !== folder?.id);
}
