<?xml version="1.0" encoding="UTF-8"?>

<xsl:stylesheet version="1.0" 
               xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
               xmlns:Atom="http://www.w3.org/2005/Atom"
               xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
               xmlns:doap="http://usefulinc.com/ns/doap#"
               exclude-result-prefixes="xsl Atom rdf doap">

    <xsl:template match="/">
        <xsl:apply-templates select="/rdf:RDF/doap:Project|/Atom:feed/Atom:entry/Atom:content/doap:Project" />
    </xsl:template>

    <xsl:output output="xml" indent="yes" encoding="utf-8" />
    
    <xsl:template match="doap:Project">
        <project>
            <created> 
                <xsl:value-of select="doap:created" />
            </created>
            <name>
                <xsl:value-of select="doap:name" />
            </name>
            <homepage> 
                <xsl:value-of select="doap:homepage/@rdf:resource" />
            </homepage>
            <description>
                <xsl:value-of select="doap:description" />
            </description>
            <bug-database>
                <xsl:value-of select="doap:bug-database/@rdf:resource" />
            </bug-database>
            <mailing-list> 
                <xsl:value-of select="doap:mailing-list/@rdf:resource" />
            </mailing-list>
            <repository> 
                <xsl:value-of select="doap:repository/*/doap:location/@rdf:resource" />
            </repository>
            <programming-languages>
                <xsl:for-each select="doap:programming-language">
                    <language> 
                        <xsl:value-of select="." />
                    </language>
                </xsl:for-each>
            </programming-languages>
            <categories>
                <xsl:for-each select="doap:category">
                    <category>
                         <xsl:value-of select="substring-after(./@rdf:resource, 'category/')" />
                    </category>
                </xsl:for-each>
            </categories>
        </project>
    </xsl:template>

</xsl:stylesheet>