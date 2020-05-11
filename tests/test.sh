java -jar antlr-4.8-complete.jar apt.g4
$JAVA_HOME/bin/javac -cp ./antlr-4.8-complete.jar:. apt*.java
java -cp antlr-4.8-complete.jar:. org.antlr.v4.gui.TestRig apt record -gui -trace -tokens ./test.txt
