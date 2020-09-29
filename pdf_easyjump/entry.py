#!/usr/bin/env python
from argparse import ArgumentParser
import os.path
import yaml
from pikepdf import Pdf, Array, Name, String, Dictionary, OutlineItem

numbering_styles = ('D', 'r', 'R', 'A', 'a', 'none')
def check_style(s):
    if s not in numbering_styles:
        return '"style" must be one of {}'.format(', '.join(numbering_styles))
    else:
        return None


def check_key(obj, key, checker, required):
    if required:
        if key not in obj:
            return '"{}" is missing'.format(key)
    if key in obj:
        value = obj[key]
        if isinstance(checker, type):
            if not isinstance(value, checker):
                return 'type of "{}" is invalid'.format(key)
        else:
            err = checker(value)
            if err:
                return err
    return None


def validate_pagelabels(page_labels):
    errs = []
    prev = -1
    for i, label in enumerate(page_labels):
        c = check_key(label, 'start', int, True)
        if c: errs.append(c + ' (page entry #{})'.format(i+1))
        c = check_key(label, 'style', check_style, True)
        if c: errs.append(c + ' (page entry #{})'.format(i+1))
        c = check_key(label, 'prefix', str, False)
        if c: errs.append(c + ' (page entry #{})'.format(i+1))
        c = check_key(label, 'initial_count', int, False)
        if c: errs.append(c + ' (page entry #{})'.format(i+1))
        if 'style' in label and label['style'] == 'none' and 'initial_count' in label:
            errs.append('"initial_count" should not exist if "style" is none (page entry #)'.format(i+1))
        if 'start' in label and isinstance(label['start'], int):
            s = label['start']
            if i > 0 and prev >= 0 and s <= prev:
                errs.append('"start" must be increasing from previous entries (page entry #{})'.format(i+1))
            prev = s
    return errs


def set_pagelabels(doc, page_labels):
    arr = []
    for label in page_labels:
        pn = label['start'] - 1 # page index 1-based -> 0-based
        d = {}
        if 'style' in label and label['style'] != 'none':
            d['/S'] = Name('/'+label['style'])
        if 'prefix' in label:
            d['/P'] = label['prefix']
        if 'initial_count' in label:
            d['/St'] = label['initial_count']
        obj = Dictionary(d)
        arr.append(pn)
        arr.append(obj)
    obj = Dictionary({'/Nums' : Array(arr)})
    doc.root[Name.PageLabels] = obj


def get_pagelabels(doc):
    if Name.PageLabels not in doc.root:
        return None
    arr = doc.root.PageLabels.Nums
    num = len(arr) // 2
    res = []
    for i in range(num):
        st = arr[i * 2] + 1 # 0-based -> 1-based
        obj = arr[i * 2 + 1]
        label = {'start': st}
        if Name.S in obj:
            label['style'] = str(obj[Name.S])[1:] # trim leading '/'
        else:
            label['style'] = 'none'
        if Name.P in obj:
            label['prefix'] = str(obj[Name.P])
        if Name.St in obj:
            label['initial_count'] = obj[Name.St]
        res.append(label)
    return res


def validate_outlines(outlines):
    errs = []

    def check_item(item, id_str=''):
        c = check_key(item, 'title', str, True)
        if c: errs.append(c + ' (outline entry #{})'.format(id_str))
        c = check_key(item, 'page', int, True)
        if c: errs.append(c + ' (outline entry #{})'.format(id_str))
        c = check_key(item, 'children', list, False)
        if c: errs.append(c + ' (outline entry #{})'.format(id_str))
        if 'children' in item and isinstance(item['children'], list):
            for i, c in enumerate(item['children']):
                check_item(c, id_str+'-'+str(id_str))

    for i, item in enumerate(outlines):
        check_item(item, str(i+1))
    return errs


def get_outlines(doc):
    objgen2pn = {}
    for i, page in enumerate(doc.pages):
        objgen2pn[page.objgen] = i + 1

    def outline_item_to_dict(item):
        res = {}
        res['title'] = item.title
        if item.destination:
            dest = item.destination
        elif item.action and item.action.S == Name.GoTo:
            dest = item.action.D
        else:
            # unsupported action
            dest = None
            res['error'] = 'unsupported action'
        if isinstance(dest, String):
            # named destination (currently unsupported)
            res['page'] = str(dest)
            res['error'] = 'named destination is currently unsupported'
        if isinstance(dest, Array):
            p_gen = dest[0].objgen
            res['page'] = objgen2pn[p_gen]
            res['options'] = ''
            for i in range(1, len(dest)):
                res['options'] += str(dest[i])
                if i < len(dest) - 1:
                    res['options'] += ' , '
        if len(item.children) > 0:
            res['children'] = list(map(outline_item_to_dict, item.children))
        return res

    res = []
    with doc.open_outline() as outline:
        for item in outline.root:
            res.append(outline_item_to_dict(item))
    return res


def set_outlines(doc, outlines):

    def dict_to_outline_item(item):
        oi = OutlineItem(item['title'], item['page'] - 1)
        if 'children' in item:
            for child in item['children']:
                ci = dict_to_outline_item(child)
                oi.children.append(ci)
        return oi

    with doc.open_outline() as doc_outline:
        n = len(doc_outline.root)
        if n > 0:
            for i in reversed(range(n)):
                del doc_outline.root[i]
        for item in outlines:
            oi = dict_to_outline_item(item)
            doc_outline.root.append(oi)


def main(in_files, out_file):
    if len(in_files) == 1:
        # extract from in_file
        if out_file is None:
            base, _ = os.path.splitext(in_files[0])
            out_file = base + '.yaml'
        doc = Pdf.open(in_files[0])
        obj = {}
        pl = get_pagelabels(doc)
        if pl is not None and len(pl) > 0:
            obj['page_labels'] = pl
        ol = get_outlines(doc)
        if ol is not None and len(ol) > 0:
            obj['outlines'] = ol
        print(obj)
        yaml.dump(obj, open(out_file, 'w', encoding='utf-8'), default_flow_style=False, sort_keys=False, allow_unicode=True)
    elif len(in_files) == 2:
        # embed outline and/or page labels
        yml = None
        pdf = None
        for f in in_files:
            if f.lower().endswith('.yaml') or f.lower().endswith('.yml'):
                yml = f
            if f.lower().endswith('.pdf'):
                pdf = f
        if yml is None:
            print('YAML is not specified')
        if pdf is None:
            print('PDF is not specified')
        if out_file is None:
            base, _ = os.path.splitext(pdf)
            out_file = base + '-modified.pdf'
        obj = yaml.safe_load(open(yml, encoding='utf-8'))
        doc = Pdf.open(pdf)
        if 'outlines' in obj:
            ol = obj['outlines']
            errs = validate_outlines(ol)
            if len(errs) > 0:
                print('validation of outlines failed...')
                for err in errs:
                    print(err)
            else:
                set_outlines(doc, ol)
        if 'page_labels' in obj:
            pl = obj['page_labels']
            errs = validate_pagelabels(pl)
            if len(errs) > 0:
                print('validation of page lables failed...')
                for err in errs:
                    print(err)
            else:
                set_pagelabels(doc, pl)
        doc.remove_unreferenced_resources()
        doc.save(out_file)


def run():
    parser = ArgumentParser(description='embed/extract outline (table of contents) & page labels to/from PDF documens')
    parser.add_argument('-o', nargs=1, dest='out_file', help='output file')
    parser.add_argument('in_files', nargs='+', help='input files')
    args = parser.parse_args()
    main(args.in_files, args.out_file)


if __name__ == '__main__':
    run()