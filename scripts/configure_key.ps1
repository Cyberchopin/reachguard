Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$form = New-Object System.Windows.Forms.Form
$form.Text = 'CallGate - AssemblyAI setup'
$form.ClientSize = New-Object System.Drawing.Size(530,210)
$form.StartPosition = 'CenterScreen'
$form.TopMost = $true
$label = New-Object System.Windows.Forms.Label
$label.Text = 'Paste your AssemblyAI API key:'
$label.Location = New-Object System.Drawing.Point(24,24)
$label.Size = New-Object System.Drawing.Size(470,24)
$box = New-Object System.Windows.Forms.TextBox
$box.UseSystemPasswordChar = $true
$box.Location = New-Object System.Drawing.Point(24,60)
$box.Size = New-Object System.Drawing.Size(480,28)
$note = New-Object System.Windows.Forms.Label
$note.Text = 'Saved locally in .env (plain text, excluded from Git). No upload in this step.'
$note.Location = New-Object System.Drawing.Point(24,102)
$note.Size = New-Object System.Drawing.Size(480,38)
$button = New-Object System.Windows.Forms.Button
$button.Text = 'Save'
$button.Location = New-Object System.Drawing.Point(200,155)
$button.Size = New-Object System.Drawing.Size(120,32)
$envFile = Join-Path (Split-Path -Parent $PSScriptRoot) '.env'
$button.Add_Click({
    $keyValue = $box.Text.Trim()
    if ($keyValue -notmatch '^[\x21-\x7e]+$') {
        [void][System.Windows.Forms.MessageBox]::Show($form,'Please paste a valid key without spaces.','Check input')
        return
    }
    try {
        $lines = @()
        if (Test-Path -LiteralPath $envFile) {
            $lines = @(Get-Content -LiteralPath $envFile | Where-Object { $_ -notmatch '^\s*ASSEMBLYAI_API_KEY=' })
        }
        $lines += 'ASSEMBLYAI_API_KEY=' + $keyValue
        [System.IO.File]::WriteAllLines($envFile, [string[]]$lines, (New-Object System.Text.UTF8Encoding($false)))
        $box.Clear()
        $keyValue = $null
        [void][System.Windows.Forms.MessageBox]::Show($form,'Saved. Return to the chat to continue.','CallGate')
        $form.Close()
    } catch {
        [void][System.Windows.Forms.MessageBox]::Show($form,'Could not save the configuration. Return to the chat.','CallGate')
    }
})
$form.Controls.AddRange(@($label,$box,$note,$button))
$form.AcceptButton = $button
$form.Add_Shown({ $form.Activate(); $box.Focus() })
[void]$form.ShowDialog()
$form.Dispose()
