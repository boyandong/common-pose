"""Verify V5.2 content, frozen data, bilingual correspondence and PDF preflight."""
from pathlib import Path
from collections import Counter
import json,re,hashlib
from pypdf import PdfReader
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def vector(path):
    def walk(resources):
        for value in resources.get('/XObject',{}).values():
            obj=value.get_object();assert obj.get('/Subtype')!='/Image',path
            if '/Resources' in obj:walk(obj['/Resources'])
    for page in PdfReader(path).pages:walk(page['/Resources'])
def main():
    old=HERE.parent/'20261014_v5_1_reader_revision'
    source=(HERE/'CommonPose_EMBC2027_V5_2_EN.tex').read_text(encoding='utf-8')
    chinese=(HERE/'CommonPose_EMBC2027_V5_2_ZH.tex').read_text(encoding='utf-8')
    previous=(old/'manuscript.tex').read_text(encoding='utf-8')
    eq=lambda t:re.findall(r'\\begin\{equation\}.*?\\end\{equation\}',t,re.S)
    assert len(eq(source))==4 and eq(source)==eq(chinese)==eq(previous)
    assert not re.search(r'\\(?:input|include|bibliography|bibliographystyle)\{',source)
    assert len(re.findall(r'\\bibitem',source))==10
    abstract=lambda t:re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',t,re.S).group(1).strip()
    assert abstract(source)==abstract(previous)
    tab=lambda t:re.search(r'\\begin\{tabular\}.*?\\end\{tabular\}',t,re.S).group()
    assert tab(source)==tab((old/'table1.tex').read_text(encoding='utf-8'))
    assert '3.790 percentage points' in source and '2.774--4.691; n=80' in source
    assert 'Differences between displayed method medians are not direct within-participant comparisons.' in source
    assert '16 participants and 60 weak-instruction recordings' in source
    assert '/U marks the training objective' in source
    assert 'the experiment does not establish the specific mechanism' in source
    assert not re.search(r'Supplementary|Tables?\s*~?S[1-5]',source)
    assert 'ACKNOWLEDG' not in source.upper()
    hashes=json.loads((HERE/'review/V5_1_BASELINE_HASHES.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/name)==digest for name,digest in hashes.items())
    original_source_hashes=json.loads((HERE/'review/FIGURE_SOURCE_HASHES.json').read_text(encoding='utf-8'))
    assert all(sha(Path(name))==digest for name,digest in original_source_hashes.items())
    assert json.loads((HERE/'review/FIGURE2_VALUES.json').read_text())==json.loads((old/'review/FIGURE2_VALUES.json').read_text())
    for name in ['fig1_compact','fig2_N80_ranking','fig3_class_fidelity']:
        for suffix in ['', '_grayscale']:vector(HERE/'figures'/(name+suffix+'.pdf'))
    mapping=json.loads((HERE/'review/BILINGUAL_PARAGRAPH_MAPPING.json').read_text(encoding='utf-8'))
    assert len(mapping)==39
    for row in mapping:
        assert row['english'] in source and row['chinese'] in chinese
        decimals=lambda s:Counter(re.findall(r'\d+\.\d+|\d{1,3}(?:,\d{3})+',s))
        assert decimals(row['english'])==decimals(row['chinese']),row['source_line']
    bibliography=lambda t:re.search(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}',t,re.S).group()
    assert bibliography(source)==bibliography(chinese)
    pages={}
    for lang in ['EN','ZH']:
        pdf=HERE/f'output/pdf/CommonPose_EMBC2027_V5_2_{lang}.pdf'
        assert sha(pdf)==sha(HERE/f'build/CommonPose_EMBC2027_V5_2_{lang}.pdf')
        reader=PdfReader(pdf);assert len(reader.pages)==5
        texts=[p.extract_text() for p in reader.pages]
        heading='REFERENCES' if lang=='EN' else '参考文献'
        assert all(heading not in t for t in texts[:4]) and heading in texts[4]
        assert len(re.findall(r'\[\d+\]',texts[4]))==10
        assert not any('??' in t for t in texts)
        log=json.loads((HERE/f'review/COMPILE_{lang}_FULL.json').read_text(encoding='utf-8-sig'))
        assert log['exitCode']==0
        final=log['log'][log['log'].rfind(f'(CommonPose_EMBC2027_V5_2_{lang}.tex'):]
        assert not any(x in final for x in ['Overfull','Missing character','undefined references','Float too large'])
        for i,t in enumerate(texts):(HERE/f'qa/{lang}_page_{i+1}.txt').write_text(t,encoding='utf-8')
        pages[lang]={'pages':5,'pdf_sha256':sha(pdf),'full_tex_sha256':sha(HERE/f'CommonPose_EMBC2027_V5_2_{lang}.tex')}
    receipt={'status':'PASS_CANDIDATE_CONTENT_DATA_BILINGUAL_PDF_CHECKS','pages':pages,
        'all_four_original_equations_exact':True,'all_24_table_medians_and_six_CIs_unchanged':True,
        'figure2_all_48_values_unchanged':True,'source_data_hashes_unchanged':True,
        'v5_1_files_unchanged':len(hashes),'bilingual_paragraphs_checked':39,'decimal_numbers_and_reference_entries_match':True,
        'direct_score_only_CI_from_frozen_source':True,'vector_color_and_grayscale_pdfs_checked':6,
        'AI_disclosure':'NOT_ADOPTED_PER_USER','authors':'USER_CONFIRMED_CURRENT_FIELDS',
        'new_experiments':False,'conference_submission_performed':False,
        'candidate_release':'READY_FOR_SUPERVISOR_REVIEW','private_github':'verified progress branch, no public availability claim'}
    (HERE/'review/VALIDATION.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='pages'}))
if __name__=='__main__':main()
