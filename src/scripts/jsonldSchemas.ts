/**
 * jsonldSchemas.ts — JSON-LD schema builders for /gsd:debug
 * link-asset-seo-audit TODO `jsonld-structured-data`.
 *
 * Returns plain objects ready to JSON.stringify into <script
 * type="application/ld+json">. Consumed by src/components/StructuredData.astro.
 *
 * All schemas use https://realufo.org as the canonical origin.
 */

const ORIGIN = 'https://realufo.org';
const PUBLISHER = {
  '@type': 'Organization',
  name: 'realufo.org',
  url: ORIGIN,
  logo: {
    '@type': 'ImageObject',
    url: `${ORIGIN}/assets/favicon.svg`,
  },
};

export function websiteSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'realufo.org',
    alternateName: 'realufo · Government UAP Archive',
    url: ORIGIN,
    description:
      'Offline-first archive of every official government UAP source — verbatim public-domain content from 15 agencies across 12 jurisdictions.',
    inLanguage: 'en',
    publisher: PUBLISHER,
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${ORIGIN}/search/?q={search_term_string}`,
      },
      'query-input': 'required name=search_term_string',
    },
  };
}

export function collectionPageSchema(opts: {
  url: string;
  name: string;
  description: string;
  items: { slug: string; title: string }[];
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: opts.name,
    url: `${ORIGIN}${opts.url}`,
    description: opts.description,
    isPartOf: { '@type': 'WebSite', url: ORIGIN, name: 'realufo.org' },
    publisher: PUBLISHER,
    inLanguage: 'en',
    hasPart: opts.items.map((item) => ({
      '@type': 'Article',
      url: `${ORIGIN}/stories/${item.slug}/`,
      headline: item.title,
    })),
  };
}

export function articleSchema(opts: {
  slug: string;
  title: string;
  description: string;
  archive: string;
  date?: string;
  image?: string;
}) {
  const url = `${ORIGIN}/stories/${opts.slug}/`;
  const datePublished = opts.date || '2026-01-01';
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: opts.title,
    description: opts.description,
    url,
    datePublished,
    dateModified: datePublished,
    inLanguage: 'en',
    publisher: PUBLISHER,
    author: PUBLISHER,
    mainEntityOfPage: { '@type': 'WebPage', '@id': url },
    image:
      opts.image && opts.image.startsWith('http')
        ? opts.image
        : `${ORIGIN}${opts.image || '/assets/favicon.svg'}`,
    isPartOf: {
      '@type': 'CollectionPage',
      url: `${ORIGIN}/stories/`,
      name: 'Stories — realufo.org',
    },
    keywords: ['UAP', 'UFO', opts.archive, 'public domain'],
  };
}

export function datasetSchema(opts: {
  slug: string;
  name: string;
  description: string;
  license: string;
  recordCount?: number;
}) {
  const url = `${ORIGIN}/${opts.slug}/`;
  return {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    name: opts.name,
    description: opts.description,
    url,
    inLanguage: 'en',
    license: opts.license,
    publisher: PUBLISHER,
    creator: PUBLISHER,
    isAccessibleForFree: true,
    distribution: [
      {
        '@type': 'DataDownload',
        encodingFormat: 'application/json',
        contentUrl: `${ORIGIN}/api/by-archive.json`,
      },
      {
        '@type': 'DataDownload',
        encodingFormat: 'application/atom+xml',
        contentUrl: `${ORIGIN}/feeds/${opts.slug}.xml`,
      },
    ],
    ...(opts.recordCount ? { variableMeasured: `${opts.recordCount} records` } : {}),
  };
}
