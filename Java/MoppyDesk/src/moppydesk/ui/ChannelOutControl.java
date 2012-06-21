/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */
package moppydesk.ui;

import javax.swing.DefaultComboBoxModel;
import javax.swing.JCheckBox;
import javax.swing.JComboBox;
import moppydesk.MoppyBridge;
import moppydesk.OutputSetting;
import moppydesk.OutputSetting.OutputType;

/**
 *
 * @author Sam
 */
public class ChannelOutControl extends javax.swing.JPanel {

    private OutputSetting settings;
    private MoppyControlWindow controlWindow;
    
    /**
     * Creates new form ChannelOutControl
     */
    public ChannelOutControl(MoppyControlWindow mcw, OutputSetting os) {
        this.settings = os;
        this.controlWindow = mcw;
        initComponents();
        loadSettings();
    }

    private void loadSettings(){
        
        enabledCB.setSelected(settings.enabled);
        
        if (settings.type.equals(OutputType.MOPPY)){
            //outputTypeRB.setSelected(moppyTypeRB.getModel(), true);
            moppyTypeRB.doClick();
        } else {
            //outputTypeRB.setSelected(MIDITypeRB.getModel(), true);
            MIDITypeRB.doClick();
        }
        
        comComboBox.setSelectedItem(settings.comPort);
        midiOutComboBox.setSelectedItem(settings.midiDeviceName);
    }
    
    private void outputTypeChanged(java.awt.event.ActionEvent evt){
        if (evt.getActionCommand().equalsIgnoreCase("Moppy")){
            settings.type = OutputType.MOPPY;
            midiOutLabel.setEnabled(false);
            midiOutComboBox.setEnabled(false);
            comComboBox.setEnabled(true);
        } else {
            settings.type = OutputType.MIDI;
            comComboBox.setEnabled(false);
            midiOutLabel.setEnabled(true);
            midiOutComboBox.setEnabled(true);
        }
    }
    
    /**
     * This method is called from within the constructor to initialize the form.
     * WARNING: Do NOT modify this code. The content of this method is always
     * regenerated by the Form Editor.
     */
    @SuppressWarnings("unchecked")
    // <editor-fold defaultstate="collapsed" desc="Generated Code">//GEN-BEGIN:initComponents
    private void initComponents() {

        outputTypeRB = new javax.swing.ButtonGroup();
        moppyTypeRB = new javax.swing.JRadioButton();
        MIDITypeRB = new javax.swing.JRadioButton();
        comComboBox = new javax.swing.JComboBox();
        midiOutComboBox = new javax.swing.JComboBox();
        midiOutLabel = new javax.swing.JLabel();
        enabledCB = new javax.swing.JCheckBox();

        setPreferredSize(new java.awt.Dimension(525, 23));

        outputTypeRB.add(moppyTypeRB);
        moppyTypeRB.setSelected(true);
        moppyTypeRB.setText("Moppy");
        moppyTypeRB.setToolTipText("Sends Moppy-protocol serial data to selected COM port");
        moppyTypeRB.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                outputTypeChanged(evt);
            }
        });

        outputTypeRB.add(MIDITypeRB);
        MIDITypeRB.setText("MIDI");
        MIDITypeRB.setToolTipText("Sends MIDI messages through to selected MIDI port");
        MIDITypeRB.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                outputTypeChanged(evt);
            }
        });

        comComboBox.setModel(new DefaultComboBoxModel(MoppyBridge.getAvailableCOMPorts()));
        comComboBox.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                comComboBoxActionPerformed(evt);
            }
        });

        midiOutComboBox.setModel(new DefaultComboBoxModel(controlWindow.availableMIDIOuts.keySet().toArray(new String[0])));
        midiOutComboBox.setEnabled(false);
        midiOutComboBox.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                midiOutComboBoxActionPerformed(evt);
            }
        });

        midiOutLabel.setText("MIDI Out:");
        midiOutLabel.setEnabled(false);

        enabledCB.setText(String.valueOf(settings.MIDIChannel));
        enabledCB.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                enabledCBActionPerformed(evt);
            }
        });

        javax.swing.GroupLayout layout = new javax.swing.GroupLayout(this);
        this.setLayout(layout);
        layout.setHorizontalGroup(
            layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
            .addGroup(layout.createSequentialGroup()
                .addContainerGap()
                .addComponent(enabledCB, javax.swing.GroupLayout.PREFERRED_SIZE, 46, javax.swing.GroupLayout.PREFERRED_SIZE)
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.UNRELATED)
                .addComponent(moppyTypeRB)
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                .addComponent(MIDITypeRB)
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.UNRELATED)
                .addComponent(comComboBox, javax.swing.GroupLayout.PREFERRED_SIZE, 63, javax.swing.GroupLayout.PREFERRED_SIZE)
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED, 104, Short.MAX_VALUE)
                .addComponent(midiOutLabel)
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                .addComponent(midiOutComboBox, javax.swing.GroupLayout.PREFERRED_SIZE, 130, javax.swing.GroupLayout.PREFERRED_SIZE)
                .addContainerGap())
        );
        layout.setVerticalGroup(
            layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
            .addGroup(javax.swing.GroupLayout.Alignment.TRAILING, layout.createSequentialGroup()
                .addGap(0, 0, Short.MAX_VALUE)
                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.BASELINE)
                    .addComponent(moppyTypeRB)
                    .addComponent(MIDITypeRB)
                    .addComponent(comComboBox, javax.swing.GroupLayout.PREFERRED_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.PREFERRED_SIZE)
                    .addComponent(midiOutComboBox, javax.swing.GroupLayout.PREFERRED_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.PREFERRED_SIZE)
                    .addComponent(midiOutLabel)
                    .addComponent(enabledCB)))
        );
    }// </editor-fold>//GEN-END:initComponents

    private void comComboBoxActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_comComboBoxActionPerformed
        settings.comPort = (String)((JComboBox)evt.getSource()).getSelectedItem();
    }//GEN-LAST:event_comComboBoxActionPerformed

    private void midiOutComboBoxActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_midiOutComboBoxActionPerformed
        settings.midiDeviceName = (String)((JComboBox)evt.getSource()).getSelectedItem();
    }//GEN-LAST:event_midiOutComboBoxActionPerformed

    private void enabledCBActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_enabledCBActionPerformed
        settings.enabled = ((JCheckBox)evt.getSource()).isSelected();
    }//GEN-LAST:event_enabledCBActionPerformed

    // Variables declaration - do not modify//GEN-BEGIN:variables
    private javax.swing.JRadioButton MIDITypeRB;
    private javax.swing.JComboBox comComboBox;
    private javax.swing.JCheckBox enabledCB;
    private javax.swing.JComboBox midiOutComboBox;
    private javax.swing.JLabel midiOutLabel;
    private javax.swing.JRadioButton moppyTypeRB;
    private javax.swing.ButtonGroup outputTypeRB;
    // End of variables declaration//GEN-END:variables
}