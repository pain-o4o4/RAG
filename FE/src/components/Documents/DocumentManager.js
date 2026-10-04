import React, { useState, useEffect, useRef } from 'react';
import { Button, Table, Spinner, Badge, UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap';
import { toast } from 'react-toastify';
import { getDocumentsApi, uploadDocumentsApi, deleteDocumentApi } from '../../services/ragService';
import './DocumentManager.scss';

const DocumentManager = ({ isLoggedIn }) => {
    const [documents, setDocuments] = useState([]);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [activeTabType, setActiveTabType] = useState('ALL');
    const [viewMode, setViewMode] = useState('LIST');
    const [searchQuery, setSearchQuery] = useState('');
    const [isSearchActive, setIsSearchActive] = useState(false);
    const fileInputRef = useRef(null);

    useEffect(() => {
        if (isLoggedIn) {
            fetchDocuments();
        }
    }, [isLoggedIn]);

    const fetchDocuments = async () => {
        setLoading(true);
        try {
            const res = await getDocumentsApi();
            if (res && res.items) {
                setDocuments(res.items);
            }
        } catch (error) {
            console.error('Lỗi khi tải tài liệu:', error);
            toast.error('Không thể tải danh sách tài liệu');
        }
        setLoading(false);
    };

    const handleUploadClick = () => {
        fileInputRef.current.click();
    };

    const handleFileChange = async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        setUploading(true);
        try {
            const res = await uploadDocumentsApi(formData);
            if (res && res.uploaded) {
                toast.success(`Đã tải lên thành công ${res.uploaded.length} tài liệu`);
                fetchDocuments();
            }
            if (res && res.failed && res.failed.length > 0) {
                res.failed.forEach(item => {
                    toast.error(`Lỗi file ${item.filename || ''}: ${item.reason || ''}`);
                });
            }
        } catch (error) {
            console.error('Lỗi tải lên:', error);
            toast.error(error.response?.data?.detail || 'Lỗi khi tải lên tài liệu');
        }
        setUploading(false);
        e.target.value = null; // reset
    };

    const handleDelete = async (id) => {
        if (!window.confirm('Bạn có chắc chắn muốn xóa tài liệu này?')) return;
        try {
            await deleteDocumentApi(id);
            toast.success('Xóa tài liệu thành công');
            fetchDocuments();
        } catch (error) {
            console.error('Lỗi khi xóa:', error);
            toast.error('Lỗi khi xóa tài liệu');
        }
    };

    const renderStatus = (status) => {
        switch (status) {
            case 'COMPLETED':
                return <Badge color="success">Hoàn thành</Badge>;
            case 'PROCESSING':
                return <Badge color="warning">Đang xử lý</Badge>;
            case 'PENDING':
                return <Badge color="secondary">Chờ xử lý</Badge>;
            case 'FAILED':
                return <Badge color="danger">Lỗi</Badge>;
            default:
                return <Badge color="light">{status}</Badge>;
        }
    };

    const formatBytes = (bytes, decimals = 2) => {
        if (!+bytes) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    };

    const formatDate = (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        const day = date.getDate();
        const month = date.getMonth() + 1;
        return `${day} thg ${month}`;
    };

    const formatFileType = (mimeType) => {
        if (!mimeType) return 'Tệp';
        const typeStr = mimeType.toLowerCase();
        if (typeStr.includes('pdf')) return 'PDF';
        if (typeStr.includes('wordprocessingml') || typeStr.includes('msword')) return 'Word';
        if (typeStr.includes('spreadsheetml') || typeStr.includes('excel')) return 'Excel';
        if (typeStr.includes('text/plain')) return 'Văn bản';
        if (typeStr.includes('image/')) return 'Ảnh';
        return 'Tệp';
    };

    const getFilteredAndSortedDocs = () => {
        let filtered = documents;
        if (activeTabType !== 'ALL') {
            filtered = filtered.filter(doc => {
                const type = formatFileType(doc.file_type).toUpperCase();
                if (activeTabType === 'PDF' && type === 'PDF') return true;
                if (activeTabType === 'WORD' && type === 'WORD') return true;
                if (activeTabType === 'TXT' && type === 'VĂN BẢN') return true;
                return false;
            });
        }
        if (searchQuery.trim() !== '') {
            filtered = filtered.filter(doc => doc.filename.toLowerCase().includes(searchQuery.toLowerCase()));
        }
        // Always sort newest first (already sorted by API, but we can enforce it)
        return filtered;
    };

    const displayDocs = getFilteredAndSortedDocs();

    return (
        <div className="document-manager-container">
            <div className="manager-content-wrapper">
                <div className="manager-top-nav">
                    <div className="nav-tabs-left">
                        {['ALL', 'PDF', 'WORD', 'TXT'].map(tab => (
                            <button
                                key={tab}
                                className={`nav-tab ${activeTabType === tab ? 'active' : ''}`}
                                onClick={() => setActiveTabType(tab)}
                            >
                                {tab === 'ALL' ? 'Tất cả' : tab}
                            </button>
                        ))}
                    </div>
                    <div className="nav-actions-right">
                        <div className={`search-box ${isSearchActive || searchQuery ? 'active' : ''}`}>
                            <button className="icon-btn" onClick={() => setIsSearchActive(!isSearchActive)}>
                                <i className="fas fa-search"></i>
                            </button>
                            {(isSearchActive || searchQuery) && (
                                <input 
                                    type="text" 
                                    className="search-input" 
                                    placeholder="Tìm kiếm tài liệu..." 
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    autoFocus
                                    onBlur={() => {
                                        if (!searchQuery) setIsSearchActive(false);
                                    }}
                                />
                            )}
                        </div>

                        <UncontrolledDropdown>
                            <DropdownToggle tag="button" className="icon-btn">
                                <i className="fas fa-sliders-h"></i>
                            </DropdownToggle>
                            <DropdownMenu dark right className="custom-dropdown options-dropdown">
                                <div className="dropdown-section">
                                    <div className="section-title">Xem</div>
                                    <DropdownItem onClick={() => setViewMode('GRID')} className="d-flex justify-content-between">
                                        Lưới {viewMode === 'GRID' && <i className="fas fa-check"></i>}
                                    </DropdownItem>
                                    <DropdownItem onClick={() => setViewMode('LIST')} className="d-flex justify-content-between">
                                        Danh sách {viewMode === 'LIST' && <i className="fas fa-check"></i>}
                                    </DropdownItem>
                                </div>
                            </DropdownMenu>
                        </UncontrolledDropdown>
                        <button className="btn-upload-pill" onClick={handleUploadClick} disabled={uploading}>
                            {uploading ? <Spinner size="sm" /> : 'Tải tệp lên'}
                        </button>
                        <input
                            type="file"
                            multiple
                            className="hidden-file-input"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            accept=".pdf,.docx,.txt"
                        />
                    </div>
                </div>

                <div className="manager-body">
                    {!isLoggedIn ? (
                        <div className="text-center py-5">
                            <i className="fas fa-lock fs-1 text-muted mb-3 d-block"></i>
                            <h5>Vui lòng đăng nhập để xem và quản lý tài liệu.</h5>
                        </div>
                    ) : (
                        <>
                            {loading ? (
                                <div className="text-center py-5">
                                    <Spinner color="primary" />
                                </div>
                            ) : viewMode === 'LIST' ? (
                                <div className="table-responsive">
                                    <Table hover className="align-middle manager-table">
                                        <thead>
                                            <tr>
                                                <th style={{ width: '40%' }}>Tên người dùng</th>
                                                <th style={{ width: '15%' }}>Loại</th>
                                                <th style={{ width: '15%' }}>Trạng thái</th>
                                                {/* <th style={{ width: '12%' }}>Đã chia sẻ</th> */}
                                                <th style={{ width: '12%' }}>Đã tạo <i className="fas fa-arrow-down ms-1" style={{ fontSize: '0.75rem' }}></i></th>
                                                <th className="text-center" style={{ width: '6%' }}></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {displayDocs.length > 0 ? (
                                                displayDocs.map(doc => (
                                                    <tr key={doc.id}>
                                                        <td title={doc.filename} className="col-filename">
                                                            <div className="filename-wrapper">
                                                                <div className="file-icon-box">
                                                                    <i className="far fa-file-alt"></i>
                                                                </div>
                                                                <span className="file-name-text">{doc.filename}</span>
                                                            </div>
                                                        </td>
                                                        <td className="text-muted">{formatFileType(doc.file_type)}</td>
                                                        <td>{renderStatus(doc.status)}</td>
                                                        {/* <td className="text-muted">Riêng tư</td> */}
                                                        <td className="text-muted">{formatDate(doc.created_at)}</td>
                                                        <td className="text-center">
                                                            <UncontrolledDropdown>
                                                                <DropdownToggle tag="span" className="action-dots">
                                                                    <i className="fas fa-ellipsis-h"></i>
                                                                </DropdownToggle>
                                                                <DropdownMenu dark right className="custom-dropdown">
                                                                    <DropdownItem onClick={() => handleDelete(doc.id)} className="text-danger">
                                                                        Xóa tài liệu
                                                                    </DropdownItem>
                                                                </DropdownMenu>
                                                            </UncontrolledDropdown>
                                                        </td>
                                                    </tr>
                                                ))
                                            ) : (
                                                <tr>
                                                    <td colSpan="6" className="text-center py-4 text-muted">
                                                        Chưa có tài liệu nào.
                                                    </td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </Table>
                                </div>
                            ) : (
                                <div className="document-grid">
                                    {displayDocs.length > 0 ? (
                                        displayDocs.map(doc => (
                                            <div key={doc.id} className="doc-card">
                                                <div className="doc-card-icon">
                                                    <i className="far fa-file-alt"></i>
                                                </div>
                                                <div className="doc-card-info">
                                                    <div className="doc-title" title={doc.filename}>{doc.filename}</div>
                                                    <div className="doc-meta">
                                                        {formatFileType(doc.file_type)} • {formatDate(doc.created_at)}
                                                    </div>
                                                </div>
                                                <UncontrolledDropdown className="doc-card-action">
                                                    <DropdownToggle tag="span" className="action-dots">
                                                        <i className="fas fa-ellipsis-h"></i>
                                                    </DropdownToggle>
                                                    <DropdownMenu dark right className="custom-dropdown">
                                                        <DropdownItem onClick={() => handleDelete(doc.id)} className="text-danger">Xóa</DropdownItem>
                                                    </DropdownMenu>
                                                </UncontrolledDropdown>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-center py-5 text-muted w-100">
                                            Chưa có tài liệu nào.
                                        </div>
                                    )}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DocumentManager;
