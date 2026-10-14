import json
from pathlib import Path
import pytest
from web.research_files import ResearchFiles, FileConflict, FileValidationError


def test_atomic_immutable_bundle_and_metadata(tmp_path):
    files=ResearchFiles(tmp_path/'research')
    result=files.save('venue_search',{'search.json':{'title':'емоція'}},identifier='my-search',metadata={'status':'zero_results'})
    assert result['files']==['manifest.json','search.json']
    assert result['relative_path']=='research/my-search'
    assert json.loads(files.path('my-search','search.json').read_text(encoding='utf-8'))['title']=='емоція'
    assert files.list()==[result]
    with pytest.raises(FileConflict):
        files.save('venue_search',{'search.json':{}},identifier='my-search')
    assert not list((tmp_path/'research').glob('.*'))


@pytest.mark.parametrize('identifier',['../escape','a/b','.', '', 'a'*65,'київ'])
def test_unsafe_identifiers(tmp_path,identifier):
    with pytest.raises(FileValidationError):
        ResearchFiles(tmp_path/'research').save('x',{'search.json':{}},identifier=identifier)
    assert not (tmp_path/'research').exists()


def test_reservation_collision_before_mutation_and_cleanup(tmp_path):
    files=ResearchFiles(tmp_path/'research')
    with files.reserve('one'):
        with pytest.raises(FileConflict):
            with files.reserve('one'):
                pytest.fail('reservation entered')
    with files.reserve('one') as reservation:
        result=reservation.save('x',{'search.json':{}})
        with pytest.raises(FileConflict):
            reservation.save('x',{'search.json':{}})
    assert result['identifier']=='one'


def test_symlink_root_parent_bundle_file_denied(tmp_path):
    actual=tmp_path/'actual';actual.mkdir()
    link=tmp_path/'link';link.symlink_to(actual,target_is_directory=True)
    with pytest.raises(FileValidationError):
        ResearchFiles(link/'research').save('x',{'search.json':{}})
    files=ResearchFiles(tmp_path/'research')
    files.save('x',{'search.json':{}},identifier='one')
    path=files.path('one','search.json');path.unlink();path.symlink_to(actual/'secret')
    with pytest.raises(FileValidationError):
        files.path('one','search.json')
    (files.root/'two').symlink_to(actual,target_is_directory=True)
    with pytest.raises(FileConflict):
        files.save('x',{'search.json':{}},identifier='two')
    assert len(files.list())==1


def test_unsupported_and_oversized_files_cleanup(tmp_path):
    files=ResearchFiles(tmp_path/'research')
    for data in ({'secret.txt':'no'},{'manifest.json':{}},{'search.json':'a'*5_000_001}):
        with pytest.raises(FileValidationError):
            files.save('x',data,identifier='bad')
        assert not (files.root/'bad').exists()
        assert not list(files.root.glob('.*'))
    with pytest.raises(FileValidationError):
        files.path('one','../secret')


def test_write_failure_is_not_visible(monkeypatch,tmp_path):
    files=ResearchFiles(tmp_path/'research')
    monkeypatch.setattr('web.research_files.os.rename',lambda *a:(_ for _ in ()).throw(OSError('disk failure')))
    with pytest.raises(OSError):
        files.save('x',{'search.json':{}},identifier='failed')
    assert files.list()==[] and not list(files.root.iterdir())


def test_reservation_portable_without_no_follow(monkeypatch,tmp_path):
    import os
    monkeypatch.delattr(os,'O_NOFOLLOW',raising=False)
    files=ResearchFiles(tmp_path/'research')
    result=files.save('x',{'search.json':{}},identifier='portable')
    assert files.path(result['identifier'],'manifest.json').is_file()
    actual=tmp_path/'actual';actual.mkdir()
    link=tmp_path/'link';link.symlink_to(actual,target_is_directory=True)
    with pytest.raises(FileValidationError):
        ResearchFiles(link).save('x',{'search.json':{}})


def test_metadata_walk_counts_invalid_entries(monkeypatch,tmp_path):
    files=ResearchFiles(tmp_path/'research');files.root.mkdir()
    scanned=[]
    def entries(path):
        for index in range(2000):
            scanned.append(index)
            yield path/f'.invalid-{index}'
    monkeypatch.setattr(Path,'iterdir',entries)
    assert files.list()==[]
    assert len(scanned)==1001


def test_private_permissions_where_supported(tmp_path):
    import os
    if os.name=='nt':
        pytest.skip('POSIX owner mode bits are unavailable on Windows')
    files=ResearchFiles(tmp_path/'research');files.save('x',{'search.json':{}},identifier='private')
    assert files.path('private','search.json').stat().st_mode & 0o777 == 0o600
    assert (files.root/'private').stat().st_mode & 0o777 == 0o700


def test_safe_leading_hyphen_underscore_identifiers(tmp_path):
    files=ResearchFiles(tmp_path/'research')
    for identifier in ('_topic','-topic'):
        assert files.save('x',{'search.json':{}},identifier=identifier)['identifier']==identifier
    assert len(files.list())==2


@pytest.mark.parametrize('identifier', ['CON','prn','AuX','nul',*[f'COM{x}' for x in range(1,10)],*[f'lpt{x}' for x in range(1,10)]])
def test_windows_device_identifiers_rejected_before_reservation(tmp_path,identifier):
    with pytest.raises(FileValidationError,match='reserved device'):
        ResearchFiles(tmp_path/'research').save('x',{'search.json':{}},identifier=identifier)
    assert not (tmp_path/'research').exists()


@pytest.mark.parametrize('identifier',['CON-topic','topic_CON','COM0','COM10','LPT0','LPT10','AUXiliary'])
def test_windows_device_word_compositions_are_valid(tmp_path,identifier):
    files=ResearchFiles(tmp_path/'research')
    assert files.save('x',{'search.json':{}},identifier=identifier)['identifier']==identifier


@pytest.mark.parametrize('fields',[{'created_at':123},{'files':'search.json'},{'files':['private.txt']},{'files':[{}]},{'kind':[]},{'metadata':[]},{'relative_path':'../escape'}])
def test_corrupted_manifest_shapes_ignored(tmp_path,fields):
    files=ResearchFiles(tmp_path/'research')
    files.save('x',{'search.json':{}},identifier='valid')
    corrupted=files.save('x',{'search.json':{}},identifier='invalid')
    path=files.path('invalid','manifest.json')
    path.write_text(json.dumps(corrupted|fields),encoding='utf-8')
    assert [item['identifier'] for item in files.list()]==['valid']


def test_recursive_manifest_json_ignored(tmp_path):
    files=ResearchFiles(tmp_path/'research')
    files.save('x',{'search.json':{}},identifier='recursive')
    files.path('recursive','manifest.json').write_text('['*2000+'0'+']'*2000,encoding='utf-8')
    assert files.list()==[]
