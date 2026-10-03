import React, { Component } from 'react';
import { connect } from 'react-redux';
import { Modal, ModalHeader, ModalBody, ModalFooter, Button } from 'reactstrap';
import * as actions from '../store/actions';
import './ConfirmModal.scss';

class ConfirmModal extends Component {
    onConfirm = () => {
        const { contentOfConfirmModal } = this.props;
        if (contentOfConfirmModal.handleFunc) {
            contentOfConfirmModal.handleFunc(contentOfConfirmModal.dataFunc);
        }
        this.onCancel();
    };

    onCancel = () => {
        this.props.setContentOfConfirmModal({
            isOpen: false,
            message: '',
            handleFunc: null,
            dataFunc: null
        });
    };

    render() {
        const { contentOfConfirmModal } = this.props;
        return (
            <Modal isOpen={contentOfConfirmModal.isOpen} toggle={this.onCancel} centered className="confirm-modal">
                <ModalHeader toggle={this.onCancel}>
                    Xác nhận
                </ModalHeader>
                <ModalBody>
                    {contentOfConfirmModal.message || 'Bạn có chắc chắn muốn thực hiện thao tác này?'}
                </ModalBody>
                <ModalFooter>
                    <Button color="secondary" onClick={this.onCancel}>
                        Hủy bỏ
                    </Button>
                    <Button color="primary" onClick={this.onConfirm}>
                        Đồng ý
                    </Button>
                </ModalFooter>
            </Modal>
        );
    }
}

const mapStateToProps = (state) => ({
    contentOfConfirmModal: state.app.contentOfConfirmModal
});

const mapDispatchToProps = (dispatch) => ({
    setContentOfConfirmModal: (data) => dispatch(actions.setContentOfConfirmModal(data))
});

export default connect(mapStateToProps, mapDispatchToProps)(ConfirmModal);
