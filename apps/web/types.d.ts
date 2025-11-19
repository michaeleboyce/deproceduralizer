declare module 'html-react-parser' {
    import { ReactElement } from 'react';

    export interface DOMNode {
        type: 'text' | 'tag' | 'script' | 'style' | 'comment';
        data?: string;
        name?: string;
        attribs?: { [key: string]: string };
        children?: DOMNode[];
        parent?: DOMNode;
    }

    export interface Element extends DOMNode {
        type: 'tag' | 'script' | 'style';
        name: string;
        children: DOMNode[];
    }

    export interface HTMLReactParserOptions {
        replace?: (domNode: DOMNode) => ReactElement | void | undefined | null | false | string;
    }

    export default function parse(html: string, options?: HTMLReactParserOptions): ReactElement | ReactElement[] | string;
}
