// A nested object of translated strings, keyed semantically (for example saleStatus.PAID).
export interface TranslationTree {
  [key: string]: string | TranslationTree;
}

// The same keys as an English tree, with any string values: the Tamil tree must match it.
export type TranslationsMatching<EnglishTree> = {
  [Key in keyof EnglishTree]: EnglishTree[Key] extends string
    ? string
    : TranslationsMatching<EnglishTree[Key]>;
};

// Lists every leaf key as a dotted path, for example "saleStatus.PAID".
export function listTranslationKeys(tree: TranslationTree, parentPath = ''): string[] {
  return Object.entries(tree).flatMap(([key, value]) => {
    const path = parentPath === '' ? key : `${parentPath}.${key}`;
    return typeof value === 'string' ? [path] : listTranslationKeys(value, path);
  });
}

// Gives the keys present in the reference tree but missing (or empty) in the candidate tree.
export function findMissingTranslationKeys(
  referenceTree: TranslationTree,
  candidateTree: TranslationTree,
): string[] {
  const candidateKeys = new Set(
    listTranslationKeys(candidateTree).filter(
      (key) => readTranslation(candidateTree, key)?.trim() !== '',
    ),
  );
  return listTranslationKeys(referenceTree).filter((key) => !candidateKeys.has(key));
}

// Reads one leaf by its dotted path, or undefined when the path is not a string leaf.
function readTranslation(tree: TranslationTree, dottedPath: string): string | undefined {
  let node: string | TranslationTree | undefined = tree;
  for (const key of dottedPath.split('.')) {
    if (node === undefined || typeof node === 'string') return undefined;
    node = node[key];
  }
  return typeof node === 'string' ? node : undefined;
}
